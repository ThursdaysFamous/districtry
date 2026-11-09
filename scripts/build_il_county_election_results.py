#!/usr/bin/env python3
"""
Fold the Illinois county clerks' precinct results into the Illinois app's
election-results files beside Chicago's, for build_chicago_election_results.py
(its --counties option calls add_counties() here; nothing runs this alone but
its --selftest).

WHICH COUNTIES. Those whose precinct outlines the Illinois map draws AND whose
clerk publishes precinct-by-precinct results a script may read:

    DeKalb, Franklin, Henry, Pike, Randolph, Wayne
        read by il_platinum_election_results_scraper.py
    Kane
        read by il_kane_election_results_scraper.py
    DuPage, Lake, McHenry, Winnebago (outside Rockford), McLean (outside
    Bloomington), the City of Bloomington, Sangamon, Macoupin
        read by il_clarity_election_results_reader.py from the Clarity reports
        a person downloads by hand (no scheduled job fetches Clarity), so
        these stay at the numbers of the last hand download

Each is its own office on the map: a precinct key names its county before a
colon ("kane:AU01", "dekalb:AF 01"), the index lists each county under
`sources`, and a contest counted by more than one office carries `bySource`,
each office's own totals (engine election-results block, "MORE THAN ONE
PUBLISHER ON ONE MAP").

THE JOIN TO THE MAP. A key's part after the colon is exactly the property the
app's precinct loader for that county writes (MAPS below), so the engine finds
the results for a clicked outline without a lookup table. The clerk's own
precinct names are matched to the map's here, and the build fails on a result
precinct that matches no outline, two that match one, or an outline left with
no results, so no precinct is drawn with another's numbers or left blank:
  Franklin, Pike   the same names, matched without case or punctuation
  Henry            the clerk writes a township with one precinct bare ("ALBA"),
                   the map "Alba 1"
  Wayne            spacing and punctuation ("GOLDENGATE", "MT. ERIE"), and one
                   spelling (the clerk's MASSILON is the map's Massillon)
  Randolph         spacing ("WINE HILL"/"WINEHILL"), one abbreviation (PRAIRIE
                   DU ROCHER is the map's "PR DU ROCHER"); the map draws Red
                   Bud 5 as two shapes, and both carry that precinct's numbers
  DeKalb           the clerk names a township and a number ("AFTON 1"), the
                   map a two-letter code and two digits ("AF 01"), and the
                   codes are il/data/app/dekalb-precinct-townships.json's
  Kane             the clerk pads the number to four digits ("AU0001"), the
                   map to two ("AU01")
  The Clarity      the same names without case, punctuation or leading
  counties         zeros ("Addison 001"/"ADDISON 1"); a township with one
                   precinct matched bare; Bloomington's precincts are the ones
                   McLean's layer names "City of Bloomington N", keyed to the
                   Bloomington Election Commission ("bloomington:...")

ONE RACE ACROSS OFFICES. A race on several offices' ballots (the statewide
offices, a U.S. House or legislative district, a regional superintendent, an
appellate or circuit judgeship, a judge's retention, a ballot question put to
a district crossing a county line) becomes ONE contest, so its colours run
across the county line. Its name is Chicago's where Chicago counts it and
otherwise written here from the clerk's title (CANONICAL below); its choices
are the first office's in that office's ballot order with any choice another
office lists added after, so a candidate keeps one colour on the whole map.
A candidate is matched across offices by the letters of the name, with a
close-spelling fallback (Pike prints "Arron B. Del Mar", Wayne "Christian
Mithcell") that must pick one choice and only one. A clerk's generic WRITE-IN
line is counted in the race's votes and not listed as a choice, and a "No
Candidate" line (an empty ballot position) is dropped, and must be zero.

WHERE A RACE REACHES BEYOND AN OFFICE'S GROUND, its card says the office's
totals are not the whole race. Statewide offices always do. A U.S. House or
legislative district does when more than half a percent of its area lies
outside the county, measured with shapely against il/data/app's district and
county outline files on every build, so a district wholly inside Kane or
DeKalb says so. A county's own offices and board never do; a regional
superintendent does where the region names more than this county; a judge
does except in a circuit of one county (Kane's 16th, DuPage's 18th, Lake's
19th, McHenry's 22nd) or a resident judgeship named for one county; a ballot question does where its text names more than one county.

Usage (via the Chicago builder):
    python3 scripts/build_chicago_election_results.py RAW --election-date 2026-11-03 \\
        --counties /tmp/platinum_raw.json --counties /tmp/kane_raw.json \
        --counties il/data/source/election-results-clarity-raw.json
"""

import difflib
import hashlib
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
APP_DATA = os.path.join(HERE, "..", "il", "data", "app")

# tag -> where the map's precinct names come from: a shipped file and the
# property its features carry, or the live layer the app's loader reads.
MAPS = {
    "dekalb": ("arcgis", "https://services7.arcgis.com/hEXJrPwm89CLXBYe/arcgis/rest/services/"
               "Precincts/FeatureServer/1", "name"),
    "franklin": ("file", "franklin-precincts.json", "name"),
    "henry": ("file", "henry-precincts.json", "name"),
    "kane": ("arcgis", "https://services1.arcgis.com/oRKmdBXD6EbdmVgJ/arcgis/rest/services/"
             "KaneCo_IL_ElectionsPrecincts/FeatureServer/1", "PRECINCT"),
    "pike": ("file", "pike-precincts.json", "name"),
    "randolph": ("arcgis", "https://services5.arcgis.com/pweYHqdOby1TE9DD/arcgis/rest/services/"
                 "VotingPrecincts/FeatureServer/1", "name"),
    "wayne": ("file", "wayne-precincts.json", "name"),
    # the Clarity counties (il_clarity_election_results_reader.py), each read
    # from the layer the app's own precinct loader reads
    "dupage": ("arcgis", "https://services.arcgis.com/neJvtQ4PXvnQ86MJ/arcgis/rest/services/"
               "Precincts_2024/FeatureServer/0", "PrecinctName"),
    "lake": ("arcgis", "https://services3.arcgis.com/HESxeTbDliKKvec2/arcgis/rest/services/"
             "LakeCounty_PoliticalBoundaries/FeatureServer/7", "TWP_PCT"),
    "mchenry": ("arcgis", "https://services1.arcgis.com/6iYC5AXXYapRVNzl/arcgis/rest/services/"
                "Voting_Precincts/FeatureServer/0", "PrecinctName"),
    "winnebago": ("arcgis", "https://maps.wingis.org/public/rest/services/WardsAndDistricts/MapServer/7", "PCTNAME"),
    "mclean": ("arcgis", "https://gis.mcleancountyil.gov/arcgis/rest/services/Clerks/PollingPlaces/MapServer/1",
               "NAME"),
    "sangamon": ("arcgis", "https://services.arcgis.com/XqG0RpqsNfIBGGb2/arcgis/rest/services/"
                 "ApprovedPrecincts20231012/FeatureServer/0", "Name"),
    "macoupin": ("socrata", "https://data.macoupincountyil.gov/resource/ab79-cnsh.json", "name"),
}
# Two offices count one county's precincts on one layer: the City of
# Bloomington's Election Commission counts the McLean precincts the map names
# "City of Bloomington <n>", and the McLean County Clerk the rest. office ->
# (the map it shares, whether a map name is this office's).
SHARED_MAPS = {
    "bloomington": ("mclean", lambda n: n.startswith("City of Bloomington ")),
    "mclean": ("mclean", lambda n: not n.startswith("City of Bloomington ")),
}
# The order the counties are listed in `sources`, after Chicago.
COUNTY_ORDER = ["kane", "dekalb", "henry", "pike", "randolph", "franklin", "wayne",
                "dupage", "lake", "mchenry", "winnebago", "mclean", "bloomington", "sangamon", "macoupin"]
# Counties a part file is split for by township (the name before the number),
# as Kane's is by its two-letter township prefix, so a click loads one
# township's precincts rather than the county's.
SPLIT_BY_TOWNSHIP = ("dupage", "lake", "mchenry", "sangamon")
# Clerk spelling -> map spelling, compared after norm().
ALIASES = {
    "wayne": {"MASSILON": "MASSILLON"},
    "randolph": {"PRAIRIEDUROCHER": "PRDUROCHER"},
}
UNCOUNTED = ("The clerk is still counting mail ballots postmarked by Election Day that "
             "arrive by November 17.")
ORDINALS = {
    "FIRST": 1, "SECOND": 2, "THIRD": 3, "FOURTH": 4, "FIFTH": 5, "SIXTH": 6, "SEVENTH": 7,
    "EIGHTH": 8, "NINTH": 9, "TENTH": 10, "ELEVENTH": 11, "TWELFTH": 12, "THIRTEENTH": 13,
    "FOURTEENTH": 14, "FIFTEENTH": 15, "SIXTEENTH": 16, "SEVENTEENTH": 17, "EIGHTEENTH": 18,
    "NINETEENTH": 19, "TWENTIETH": 20, "TWENTY-FIRST": 21, "TWENTY-SECOND": 22,
    "TWENTY-THIRD": 23, "TWENTY-FOURTH": 24,
}


class CountyError(Exception):
    pass


def norm(text):
    return re.sub(r"[^A-Z0-9]", "", str(text).upper())


def ordinal(n):
    n = int(n)
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return "%d%s" % (n, suffix)


# The circuit a county's own retention titles leave unnamed ("CIRCUIT COURT
# JUDGE ... SEEKING RETENTION IN OFFICE"): Kane is the whole 16th Circuit.
CIRCUIT_OF = {"Kane": 16, "DuPage": 18, "Lake": 19, "McHenry": 22}
# Circuits made of one county alone, so a circuit judge's race there is the
# whole race (705 ILCS 35/1: the 16th is Kane, the 18th DuPage,
# the 19th Lake and the 22nd McHenry).
ONE_COUNTY_CIRCUITS = {16: "Kane", 18: "DuPage", 19: "Lake", 22: "McHenry"}
# The county outline a shared office's ground is measured against.
OUTLINE_OF = {"bloomington": "mclean"}
# A ballot question Kane heads with the body it is put to, and whether that
# body's ground reaches past Kane County. Aurora lies in Kane, DuPage, Kendall
# and Will; Community Unit School District 300 in Kane, McHenry, Cook and
# DeKalb (DeKalb's own ballot says so); Oswego 308 and Yorkville 115 are
# Kendall County districts reaching into Kane; St. Charles 303 reaches into
# DuPage. St. Charles Township is in Kane alone. A question not listed here
# and naming no second county is read as wholly inside the county.
QUESTION_BEYOND = {
    ("Kane", "CITYOFAURORA"): True, ("Kane", "COMMUNITY300"): True, ("Kane", "OSWEGO308"): True,
    ("Kane", "YORKVILLE115"): True, ("Kane", "STCHARLES303"): True, ("Kane", "STCHARLESTWSP"): False,
}
COUNTY_CASE = {"DEKALB": "DeKalb", "MCHENRY": "McHenry", "LASALLE": "LaSalle", "DEWITT": "DeWitt",
               "JODAVIESS": "Jo Daviess", "MCLEAN": "McLean", "DUPAGE": "DuPage", "BUREUA": "Bureau", "HARDEN": "Hardin"}


def county_case(text):
    t = re.sub(r"\s+", " ", text).strip()
    return COUNTY_CASE.get(norm(t), titled(t) if t == t.upper() else t)


# ---------------------------------------------------------------- the map

def map_names(tag, offline=None):
    """The map's precinct names for one office, as the app's loader writes them."""
    if tag in SHARED_MAPS:
        layer, mine = SHARED_MAPS[tag]
        return [n for n in _map_names(layer, offline) if mine(n)]
    return _map_names(tag, offline)


_names_cache = {}


def _map_names(tag, offline=None):
    if offline is not None:
        return [str(n) for n in offline[tag]]
    if tag in _names_cache:
        return _names_cache[tag]
    _names_cache[tag] = _fetch_names(tag)
    return _names_cache[tag]


def _fetch_names(tag):
    kind, where, prop = MAPS[tag]
    if kind == "socrata":
        from scraper_common import UA_HEADERS_ROSTER_BOT, UA_ROSTER_BOT, require_robots_once
        url = where + "?$select=" + prop + "&$limit=5000"
        require_robots_once(url, UA_ROSTER_BOT, headers=UA_HEADERS_ROSTER_BOT)
        req = urllib.request.Request(url, headers=dict(UA_HEADERS_ROSTER_BOT))
        with urllib.request.urlopen(req, timeout=60) as resp:
            rows = json.load(resp)
        return [str(r[prop]) for r in rows if r.get(prop) is not None]
    if kind == "file":
        doc = json.load(open(os.path.join(APP_DATA, where)))
        return [str(f["properties"][prop]) for f in doc["features"]]
    from scraper_common import UA_HEADERS_ROSTER_BOT, UA_ROSTER_BOT, require_robots_once
    url = where + "/query?where=1%3D1&outFields=" + prop + "&returnGeometry=false&f=json&resultRecordCount=2000"
    require_robots_once(url, UA_ROSTER_BOT, headers=UA_HEADERS_ROSTER_BOT)
    req = urllib.request.Request(url, headers=dict(UA_HEADERS_ROSTER_BOT))
    with urllib.request.urlopen(req, timeout=60) as resp:
        doc = json.load(resp)
    if doc.get("exceededTransferLimit") or "features" not in doc:
        raise CountyError("%s: the precinct layer did not answer whole (%s)" % (tag, str(doc)[:200]))
    return [str(r["attributes"][prop]) for r in doc["features"] if r["attributes"].get(prop) is not None]


def dekalb_codes():
    doc = json.load(open(os.path.join(APP_DATA, "dekalb-precinct-townships.json")))
    out = {}
    for code, entry in (doc.get("townships") or doc).items():
        name = entry["name"] if isinstance(entry, dict) else entry
        out[norm(name)] = code
    return out


def result_to_map(tag, result_name, names):
    """The map name a clerk's precinct name stands for, or None."""
    by_norm = {}
    for n in names:
        by_norm.setdefault(norm(n), n)
    want = norm(result_name)
    if tag == "kane":
        m = re.fullmatch(r"([A-Z]{2})(\d+)", want)
        if m:
            want = "%s%02d" % (m.group(1), int(m.group(2)))
    elif tag == "dekalb":
        m = re.fullmatch(r"(.+?)\s+(\d+)", str(result_name).strip())
        codes = dekalb_codes()
        if m and norm(m.group(1)) in codes:
            want = "%s%02d" % (codes[norm(m.group(1))], int(m.group(2)))
    elif tag == "bloomington":
        m = re.fullmatch(r"PRECINCT(\d+)", want)
        if m:
            want = norm("City of Bloomington %d" % int(m.group(1)))
    want = ALIASES.get(tag, {}).get(want, want)
    if want in by_norm:
        return by_norm[want]
    if tag == "henry" and want + "1" in by_norm:
        return by_norm[want + "1"]
    if tag in NUMBERED:
        # the same township and number, padded differently ("Addison 001" is
        # the map's "Addison 1"); a township with one precinct the clerk
        # writes bare (Sangamon's "LOAMI", the map's "LOAMI 001")
        by_num = {}
        for n in names:
            by_num.setdefault(numbered(n), []).append(n)
        got = by_num.get(numbered(result_name))
        if got is None and numbered(result_name)[1] is None:
            stem = numbered(result_name)[0]
            alone = [n for n in names if numbered(n)[0] == stem]
            got = alone if len(alone) == 1 else None
        if got and len(got) == 1:
            return got[0]
    return None


# Counties whose clerk pads a precinct number differently from the map.
NUMBERED = ("dupage", "lake", "mchenry", "winnebago", "mclean", "bloomington", "sangamon", "macoupin")


def numbered(name):
    m = re.fullmatch(r"(.*?)(\d+)", norm(name))
    return (m.group(1), int(m.group(2))) if m else (norm(name), None)


def join_precincts(tag, turnout, names):
    """clerk name -> results key, failing on any precinct left unmatched."""
    out = {}
    taken = {}
    for rname in turnout:
        mname = result_to_map(tag, rname, names)
        if mname is None:
            raise CountyError("%s: the clerk's precinct %r matches no precinct on the map" % (tag, rname))
        if mname in taken:
            raise CountyError("%s: the clerk's precincts %r and %r both match the map's %r"
                              % (tag, taken[mname], rname, mname))
        taken[mname] = rname
        out[rname] = tag + ":" + mname
    left = sorted(set(names) - set(taken))
    if left:
        raise CountyError("%s: the map's precincts %s have no results" % (tag, ", ".join(left[:8])))
    return out


# ---------------------------------------------------------------- contests

def titled(text):
    text = re.sub(r"\s+", " ", str(text)).strip()
    if text != text.upper():
        return text
    out = re.sub(r"[A-Za-z]+(?:'[A-Za-z]+)?", lambda m: m.group(0).capitalize(), text)
    # small words stay small after the first word ("Clerk and Recorder")
    return re.sub(r"(?<=\S )(And|Of|The|For|In|To|An|A)\b", lambda m: m.group(1).lower(), out)


def district_number(*texts):
    for t in texts:
        m = re.search(r"\b(\d+)(?:ST|ND|RD|TH)\b", str(t).upper())
        if m:
            return int(m.group(1))
    for t in texts:
        n = spelled_ordinal(t)
        if n is not None:
            return n
    return None


_UNITS = ["FIRST", "SECOND", "THIRD", "FOURTH", "FIFTH", "SIXTH", "SEVENTH", "EIGHTH", "NINTH"]
_TEENS = ["TENTH", "ELEVENTH", "TWELFTH", "THIRTEENTH", "FOURTEENTH", "FIFTEENTH", "SIXTEENTH",
          "SEVENTEENTH", "EIGHTEENTH", "NINETEENTH"]
_TENS = ["TWENTY", "THIRTY", "FORTY", "FIFTY", "SIXTY", "SEVENTY", "EIGHTY", "NINETY"]
_TENS_ORD = ["TWENTIETH", "THIRTIETH", "FORTIETH", "FIFTIETH", "SIXTIETH", "SEVENTIETH", "EIGHTIETH",
             "NINETIETH"]
_ORD_RE = re.compile(
    r"\b(?:(ONE )?HUNDRED(?:TH\b| (?:AND )?))?(?:(%s|%s)[- ](%s)|(%s)|(%s)|(%s))?\b" % (
        "|".join(_TENS), "|".join(_TENS_ORD), "|".join(_UNITS), "|".join(_TENS_ORD), "|".join(_TEENS),
        "|".join(_UNITS)))


def spelled_ordinal(text):
    """The first ordinal spelled out in `text` ("SEVENTY-SEVENTH" 77, "ONE
    HUNDRED EIGHTEENTH" 118, DeKalb's "SEVENTIETH-FOURTH" 74), or None."""
    up = str(text).upper()
    for m in _ORD_RE.finditer(up):
        hundred, tens, unit, tens_ord, teen, alone = m.groups()
        n = 100 if m.group(0).strip().startswith(("ONE HUNDRED", "HUNDRED")) else 0
        if tens and unit:
            n += 10 * (2 + (_TENS.index(tens) if tens in _TENS else _TENS_ORD.index(tens))) + 1 + _UNITS.index(unit)
        elif tens_ord:
            n += 10 * (2 + _TENS_ORD.index(tens_ord))
        elif teen:
            n += 10 + _TEENS.index(teen)
        elif alone:
            n += 1 + _UNITS.index(alone)
        if n:
            return n
    return None


def vacancy_of(title):
    m = re.search(r"(?i)vacancy of (?:the )?(?:Hon\.?\s*)?([^)]+)\)", title)
    return titled(m.group(1).strip()) if m else None


def judge_name(title):
    m = re.search(r"\?\s*(.+)$", title)
    if m and m.group(1).strip():
        return titled(m.group(1).strip())
    m = re.search(r"(?i)^Shall (?:Judge )?(.+?) be retained", title) or re.search(
        r"(?i)\bJUDGE (.+?) SEEKING RETENTION", title)
    return titled(m.group(1).strip()) if m else None


def court_of(title, cname=None):
    up = title.upper()
    n = district_number(title)
    if n is None and "CIRCUIT" in up and "APPELLATE" not in up:
        n = CIRCUIT_OF.get(cname)
    if n is None:
        return None, None, None
    if "APPELLATE" in up:
        return "Appellate Court, %s District" % ordinal(n), "appellate", n
    if "CIRCUIT" in up:
        return "Circuit Court, %s Circuit" % ordinal(n), "circuit", n
    if "SUPREME" in up:
        return "Supreme Court, %s District" % ordinal(n), "supreme", n
    return None, None, n


def county_office(title, cname):
    t = re.sub(r"(?i)^FOR\s+", "", title).strip()
    t = re.sub(r"(?i)\bASSESSEMENTS\b", "ASSESSMENTS", t)
    term = ""
    m = re.search(r"\((?:TO SERVE )?(?:AN )?UNEXPIRED (\d)-YEAR TERM\)", t.upper())
    if m:
        term = " (unexpired %s-year term)" % m.group(1)
    t = re.sub(r"\s*\([^)]*\)\s*", " ", t).strip()
    t = re.sub(r"(?i)^COUNTY\s+", "", t)
    return "%s, %s County%s" % (titled(t), cname, term)


def classify(title, district, cname, vote_for, choices):
    """(group, merge key, display name, extra) for one clerk contest, or None
    for a race nobody can vote in. Every rule is a pattern on the clerk's own
    title; a title no rule knows fails the build rather than guessing."""
    up = re.sub(r"\s+", " ", title.upper()).strip()
    dist = (district or "").upper()
    yes_no = sorted(norm(c) for c in choices) == ["NO", "YES"]
    if re.search(r"\bUNITED STATES SENATOR\b", up):
        return "statewide", "Senator, U.S.", "Senator, U.S.", {}
    if re.search(r"GOVERNOR (AND|&) LIEUTENANT GOVERNOR", up):
        n = "Governor & Lieutenant Governor, Illinois"
        return "statewide", n, n, {}
    for office in ("ATTORNEY GENERAL", "SECRETARY OF STATE", "COMPTROLLER"):
        if re.search(r"^(FOR )?(STATE )?" + office + r"$", up):
            n = "%s, State of Illinois" % titled(office)
            return "statewide", n, n, {}
    if re.search(r"^(FOR )?(STATE )?TREASURER$", up) and ("ILLINOIS" in dist or not dist):
        return "statewide", "Treasurer, State of Illinois", "Treasurer, State of Illinois", {}
    if "REPRESENTATIVE IN CONGRESS" in up:
        n = "U.S. Representative, %s District" % ordinal(district_number(dist, up))
        return "congress", n, n, {"district": district_number(dist, up)}
    if re.search(r"\bSTATE SENATOR\b", up):
        n = "State Senator, %s District" % ordinal(district_number(dist, up))
        return "il-senate", n, n, {"district": district_number(dist, up)}
    if re.search(r"REPRESENTATIVE (DISTRICT )?IN THE GENERAL ASSEMBLY", up):
        n = "State Representative, %s District" % ordinal(district_number(dist, up))
        return "il-house", n, n, {"district": district_number(dist, up)}
    if "REGIONAL SUPERINTENDENT" in up:
        # Platinum: "FOR REGIONAL SUPERINTENDENT OF SCHOOLS (LEE, OGLE AND
        # WHITESIDE COUNTIES)" with the region in the district column;
        # Kane: "GRUNDY & KENDALL COUNTIES FOR REGIONAL SUPERINTENDENT"
        par = re.search(r"(?i)\(([^)]*COUNT[^)]*)\)?", title) or re.search(r"^(.*?COUNT(?:Y|IES)) FOR\b", up)
        counties = []
        if par:
            text = re.sub(r"(?i)\bcount(y|ies)\b", "", par.group(1))
            counties = [county_case(c) for c in re.split(r",|&|\band\b", text, flags=re.I) if c.strip()]
        if not counties:
            raise CountyError("%s: %r names no counties" % (cname, title))
        n = "Regional Superintendent of Schools (%s %s)" % (
            ", ".join(counties[:-1]) + " and " + counties[-1] if len(counties) > 1 else counties[0],
            "Counties" if len(counties) > 1 else "County")
        # keyed by the counties, never the region number: the Clarity reports
        # name a region's counties and no number, so a number-keyed office
        # and a county-keyed one would split one race in two
        key = "counties " + ",".join(sorted(norm(c) for c in counties))
        return "regional", key, n, {"counties": counties}
    if re.search(r"\bCHAIR(MAN|PERSON|WOMAN)? OF THE COUNTY BOARD\b", up):
        # elected countywide, so not one of the board's districts
        n = "Chairperson of the County Board, %s County" % cname
        return "county", n, n, {}
    if "FOREST PRESERVE" in up or "FOREST PRESERVE" in dist:
        # Clarity counties: "PRESIDENT OF THE FOREST PRESERVE COMMISSION",
        # "FOREST PRESERVE COMMISSIONER DISTRICT 1"
        body = "%s County Forest Preserve District" % cname
        num = re.search(r"DIST(?:RICT)?\.? ?(\d+)", up) or re.search(r"DIST(?:RICT)?\.? ?(\d+)", dist)
        office = "President" if "PRESIDENT" in up else "Commissioner"
        n = "%s, %s%s" % (office, body, ", District %d" % int(num.group(1)) if num else "")
        return "county", n, n, {"seats": vote_for}
    if (re.search(r"\bCOUNTY BOARD\b", up) or re.search(r"\bCOUNTY BOARD\b", dist)) and not yes_no:
        num = re.search(r"DIST(?:RICT)?\.? (\d+)", dist) or re.search(r"DISTRICT (\d+)", up)
        where = "District %d" % int(num.group(1)) if num else "at large"
        term = ""
        m = re.search(r"(UNEXPIRED )?(\d)-YEAR TERM", up)
        if m and m.group(1):
            term = " (unexpired %s-year term)" % m.group(2)
        elif m and m.group(2) == "2":
            term = " (2-year term)"
        n = "%s County Board, %s%s" % (cname, where, term)
        return "county-board", n, n, {"seats": vote_for, "district": int(num.group(1)) if num else 0}
    if re.search(r"^(FOR )?COUNTY COMMISSIONER$", up):
        n = "Commissioner, %s County" % cname
        return "county-board", n, n, {"seats": vote_for}
    if "JUDGE OF THE" in up and "VACANCY" in up:
        court, kind, num = court_of(title, cname)
        if not court:
            raise CountyError("%s: %r names no court" % (cname, title))
        resident = cname.upper() + " COUNTY" in up
        label = {"appellate": "Appellate Court Judge, %s District",
                 "circuit": "Circuit Court Judge, %s Circuit",
                 "supreme": "Supreme Court Judge, %s District"}[kind] % ordinal(num)
        if resident:
            label += ", %s County" % cname
        n = "%s (vacancy of %s)" % (label, vacancy_of(title))
        return "judges", norm(n), n, {"court": kind, "num": num, "resident": resident}
    if yes_no and re.search(r"(?i)\bretain|\bretention\b", title) and re.search(r"(?i)\bjudge\b", title):
        court, kind, num = court_of(title, cname)
        name = judge_name(title)
        if not court or not name:
            raise CountyError("%s: cannot read the judge or court in %r" % (cname, title))
        n = "%s (%s)" % (name, court)
        return "retention", norm(n), n, {"court": kind, "num": num}
    if yes_no:
        text = re.sub(r"\s+", " ", title).strip().strip('"').strip()
        lead = re.match(r"\(([^)]+)\)", text)
        many = bool(re.search(r"(?i)\bcounties\b", text)) or bool(
            lead and QUESTION_BEYOND.get((cname, norm(lead.group(1)))))
        return "questions", norm(text), text, {"many": many}
    if re.search(r"\b(SANITARY|TRUSTEE|MAYOR|ALDERM[AE]N|VILLAGE|TOWNSHIP)\b", up):
        n = "%s (%s County ballot)" % (titled(re.sub(r"(?i)^FOR\s+", "", title)), cname)
        return "local", norm(n), n, {"seats": vote_for}
    if (re.search(r"(?i)\bCOUNTY\b", dist) and (cname.upper() in dist or dist == "COUNTY")) or (
            not dist and re.match(r"^(FOR )?COUNTY ", up)):
        n = county_office(title, cname)
        return "county", n, n, {}
    raise CountyError("%s: no rule recognises the contest %r (district %r)" % (cname, title, district))


def clean_choice(name):
    """A ballot line as a choice's display name; None for a generic write-in
    line (votes kept, no choice) and "" for an empty ballot position."""
    s = re.sub(r"\s+", " ", str(name)).strip()
    if norm(s) in ("WRITEIN", "WRITEINS", "WRITEINVOTES"):
        return None
    if norm(s) == "NOCANDIDATE":
        return ""
    if norm(s) == "REJECTEDWRITEINS":
        return False  # not a vote for anyone; counted nowhere
    if norm(s) == "UNASSIGNEDWRITEINS":
        return None
    s = re.sub(r"\s*\([A-Z]{2,4}\)\s*$", "", s)  # a party label: "(DEM)", "(AMC)"
    if norm(s) == "NOCANDIDATE":
        return ""
    if s.startswith("("):
        # a ticket printed on two lines: "(JB Pritzker (Christian Mitchell"
        parts = [p.strip().rstrip(")").strip() for p in s.split("(") if p.strip()]
        s = " & ".join(parts)
    if norm(s) in ("YES", "NO"):
        return s.title()
    if s == s.upper() and re.search(r"[A-Z]{3}", s):
        s = titled(s)
    return s


def choice_key(name):
    return re.sub(r"[^a-z]", "", re.sub(r"\s*\(write-in\)$", "", str(name), flags=re.I).lower())


def match_choice(name, choices):
    """The index of `name` among `choices`, or None."""
    k = choice_key(name)
    exact = [i for i, c in enumerate(choices) if choice_key(c) == k]
    if len(exact) == 1:
        return exact[0]
    scored = sorted(((difflib.SequenceMatcher(None, k, choice_key(c)).ratio(), i)
                     for i, c in enumerate(choices)), reverse=True)
    if scored and scored[0][0] >= 0.85 and (len(scored) == 1 or scored[1][0] < 0.85):
        return scored[0][1]
    # a ballot that prints surnames only, or the first name of a ticket only
    # (McLean's "Pritzker & Mitchell", Bloomington's "JB Pritzker" for the
    # Pritzker & Mitchell ticket): each part's surname in order, one choice only
    by_surname = [i for i, c in enumerate(choices) if surnames_match(name, c)]
    if len(by_surname) == 1:
        return by_surname[0]
    return None


def _surname(part):
    words = re.sub(r"\s*\(write-in\)$", "", part, flags=re.I).replace(",", " ").split()
    words = [w for w in words if norm(w) not in ("JR", "SR", "II", "III", "IV")]
    return norm(words[-1]) if words else ""


def surnames_match(name, choice):
    """True when `name` names `choice` by surnames: every &-part of `name`
    ends in the surname of the same part of `choice` (and has no more parts),
    and neither side is a write-in line the other is not."""
    if bool(re.search(r"(?i)\(write-in\)", str(name))) != bool(re.search(r"(?i)\(write-in\)", str(choice))):
        return False
    mine = [p for p in str(name).split("&") if p.strip()]
    theirs = [p for p in str(choice).split("&") if p.strip()]
    if not mine or len(mine) > len(theirs):
        return False
    return all(_surname(a) and _surname(a) == _surname(b) for a, b in zip(mine, theirs))


# ---------------------------------------------------------------- geometry

_shapes = {}


def _load_shapes():
    if _shapes:
        return _shapes
    from shapely.geometry import shape
    from shapely.ops import unary_union
    for group, path, prop in (("congress", "congress-districts.json", "BASENAME"),
                              ("il-senate", "il-senate-districts.json", "BASENAME"),
                              ("il-house", "il-house-districts.json", "BASENAME")):
        doc = json.load(open(os.path.join(APP_DATA, path)))
        # a TIGER file carries one "not defined" feature for the lake
        _shapes[group] = dict((int(f["properties"][prop]), shape(f["geometry"])) for f in doc["features"]
                              if str(f["properties"].get(prop, "")).isdigit())
    _shapes["county"] = {}
    for tag in COUNTY_ORDER:
        doc = json.load(open(os.path.join(APP_DATA, OUTLINE_OF.get(tag, tag) + "-county-outline.json")))
        _shapes["county"][tag] = unary_union([shape(f["geometry"]) for f in doc["features"]])
    return _shapes


def district_beyond(group, num, tag):
    """True when more than 0.5% of the district's area lies outside the county."""
    s = _load_shapes()
    if num not in s[group]:
        raise CountyError("%s: the map has no %s district %s" % (tag, group, num))
    d = s[group][num]
    outside = d.difference(s["county"][tag]).area / d.area
    return outside > 0.005


def beyond_for(group, extra, tag, cname):
    if group == "statewide":
        return True
    if group in ("congress", "il-senate", "il-house"):
        return district_beyond(group, extra["district"], tag)
    if group in ("county", "county-board"):
        return False
    if group == "regional":
        counties = [norm(c) for c in extra["counties"]]
        return not (counties == [norm(cname)])
    if group in ("judges", "retention"):
        if extra.get("resident"):
            return False
        return not (extra.get("court") == "circuit" and ONE_COUNTY_CIRCUITS.get(extra.get("num")) == cname)
    if group == "questions":
        return extra["many"]
    if group == "local":
        return False  # a body on one county's ballot alone (Kane's Wasco Sanitary District)
    return True


# ---------------------------------------------------------------- the fold

def add_counties(contests, turnout, raws, chicago_source, offline_names=None, certified=None):
    """Fold the county reads into Chicago's contests (in place) and turnout.

    contests: the Chicago builder's list ({id, name, group, choices, total,
              precincts, beyond}); each gains `bySource`.
    turnout:  {"total", "precincts"}; the counties' precincts are added.
    raws:     the scrapers' outputs, each {read, counties: [...]}.
    chicago_source: Chicago's `sources` entry.
    certified: {tag: date} for a county whose canvass is complete.
    Returns (sources, part_of for the county keys, per-county summary lines).
    """
    certified = certified or {}
    reads = {}
    for raw in raws:
        for c in raw["counties"]:
            if c["county"] in reads:
                raise CountyError("%s is in two raw reads" % c["county"])
            reads[c["county"]] = (raw, c)
    missing = [t for t in COUNTY_ORDER if t not in reads]
    if missing:
        raise CountyError("no raw read for %s" % ", ".join(missing))

    by_name = dict((c["name"], c) for c in contests)
    by_key = {}
    for c in contests:
        c["bySource"] = {"chicago": {"total": list(c["total"]), "beyond": bool(c["beyond"]),
                                     "choices": list(range(len(c["choices"])))}}
        c["_order"] = (0, int(c["id"]) if str(c["id"]).isdigit() else 0)
    sources = [chicago_source]
    summary = []
    for rank, tag in enumerate(COUNTY_ORDER, 1):
        raw, county = reads[tag]
        cname = county["name"]
        names = map_names(tag, offline_names)
        keys = join_precincts(tag, county["turnout"], names)
        cast = 0
        for rname, (reg, bal) in county["turnout"].items():
            turnout["precincts"][keys[rname]] = [reg, bal]
            cast += bal
        if cast != county["ballots"]:  # rows counted outside any precinct are apart (outsideBallots)
            raise CountyError("%s: precinct ballots add to %d, the county says %d" % (tag, cast, county["ballots"]))
        turnout["total"] = [(turnout["total"][0] or 0) + sum(v[0] for v in county["turnout"].values()),
                            (turnout["total"][1] or 0) + cast]
        sources.append({
            "id": tag, "publisher": county.get("publisher") or "%s County Clerk" % cname,
            "areaName": county.get("areaName") or "%s County" % cname, "source": county["source"],
            "read": county.get("read") or raw["read"], "certified": tag in certified,
            "certifiedDate": certified.get(tag), "uncountedNote": "" if tag in certified else UNCOUNTED,
        })
        added = 0
        for race in county["contests"]:
            if race.get("fixed"):
                # the reader already knows what this contest is (Winnebago's
                # unnamed retention questions); no title rule is asked
                group, key, display = race["fixed"]["group"], norm(race["name"]), race["name"]
                extra = {"many": bool(race["fixed"].get("beyond"))}
            else:
                group, key, display, extra = classify(race["name"], race.get("district", ""), cname,
                                                      race.get("voteFor") or 1, race["choices"])
            # the clerk's ballot lines as choices, and which raw column each is
            lines = []
            for i, ch in enumerate(race["choices"]):
                lines.append((i, clean_choice(ch)))
            for i, ch in lines:
                if ch == "":
                    if any(v[i] for v in race["precincts"].values()):
                        raise CountyError("%s, %s: an empty ballot position counted votes" % (cname, race["name"]))
            named = [(i, ch) for i, ch in lines if ch]
            if not named:
                continue  # nobody on the ballot (Wayne's District 6)
            target = by_name.get(display) if group in ("statewide", "congress", "il-senate", "il-house") else None
            if target is None:
                target = by_key.get((group, key))
            if target is None:
                cid = "x" + hashlib.sha1(("%s|%s" % (group, key)).encode()).hexdigest()[:7]
                target = {"id": cid, "name": display, "group": group, "choices": [], "precincts": {},
                          "total": [0], "beyond": False, "bySource": {},
                          "_order": (rank, extra.get("district") or 0)}
                if (extra.get("seats") or 1) > 1:
                    target["seats"] = extra["seats"]
                contests.append(target)
                by_key[(group, key)] = target
            elif group not in ("statewide", "congress", "il-senate", "il-house"):
                if target.get("seats", 1) != (extra.get("seats") or 1):
                    raise CountyError("%s: %s elects %s seats here and %s elsewhere"
                                      % (cname, display, extra.get("seats"), target.get("seats")))
            # each clerk choice's index in the merged contest
            col = {}
            for i, ch in named:
                at = match_choice(ch, target["choices"])
                if at is not None and at in col.values():
                    raise CountyError("%s, %s: two of the clerk's choices match %r"
                                      % (cname, display, target["choices"][at]))
                if at is None:
                    target["choices"].append(ch)
                    at = len(target["choices"]) - 1
                    for k, vals in target["precincts"].items():
                        vals.append(0)
                    target["total"].append(0)
                    for s in target["bySource"].values():
                        s["total"].append(0)
                col[i] = at
            width = len(target["choices"])
            tot = [0] * (width + 1)
            for rname, raw_vals in race["precincts"].items():
                k = keys[rname]
                vals = [0] * (width + 1)
                vals[0] = sum(v for i, v in enumerate(raw_vals) if v is not None and lines[i][1] is not False)
                for i, at in col.items():
                    vals[at + 1] = raw_vals[i]
                if k in target["precincts"]:
                    raise CountyError("%s: %s counted twice in %s" % (cname, rname, display))
                target["precincts"][k] = vals
                for n in range(width + 1):
                    tot[n] += vals[n]
            if tag in target["bySource"]:
                raise CountyError("%s: two of the clerk's contests are %s" % (cname, display))
            entry = {"total": tot, "beyond": beyond_for(group, extra, tag, cname),
                     "choices": sorted(col.values())}
            if race.get("outside"):
                # votes the clerk counted in no precinct: in the office's
                # totals, on no shape (DuPage's federal-only ballots)
                out = [0] * (width + 1)
                out[0] = sum(v for i, v in enumerate(race["outside"]) if lines[i][1] is not False)
                for i, at in col.items():
                    out[at + 1] = race["outside"][i]
                entry["outside"] = out
                for n in range(width + 1):
                    tot[n] += out[n]
            target["bySource"][tag] = entry
            added += 1
        summary.append("%s: %d precincts, %d contests, %d ballots" % (county.get("areaName") or cname, len(keys), added, cast))

    # every contest's totals and reach are its offices' together; values are
    # padded to the final width (a choice added by a later county)
    for c in contests:
        width = len(c["choices"])
        for vals in c["precincts"].values():
            vals.extend([0] * (width + 1 - len(vals)))
        for s in c["bySource"].values():
            s["total"].extend([0] * (width + 1 - len(s["total"])))
            if "outside" in s:
                s["outside"].extend([0] * (width + 1 - len(s["outside"])))
        outs = [s["outside"] for s in c["bySource"].values() if s.get("outside")]
        if outs:
            c["outside"] = [sum(o[n] for o in outs) for n in range(width + 1)]
        if len(c["bySource"]) > 1 or "chicago" not in c["bySource"]:
            c["total"] = [sum(s["total"][n] for s in c["bySource"].values()) for n in range(width + 1)]
        c["beyond"] = any(s["beyond"] for s in c["bySource"].values())
        if len(c["bySource"]) == 1 and "chicago" in c["bySource"]:
            del c["bySource"]  # Chicago's alone: the file-level fields speak for it
    for c in contests:
        if "bySource" in c:
            c["bySource"]["chicago"] = c["bySource"].pop("chicago") if "chicago" in c["bySource"] else None
            if c["bySource"]["chicago"] is None:
                del c["bySource"]["chicago"]

    def part_of(k):
        tag, name = k.split(":", 1)
        if tag == "kane":
            return "kane-" + norm(name)[:2]
        if tag in SPLIT_BY_TOWNSHIP:
            return tag + "-" + numbered(name)[0].lower()[:30]
        return tag
    return sources, part_of, summary


def sort_key(group_order):
    def key(c):
        num = re.search(r"\b(\d+)(?:st|nd|rd|th) (?:District|Circuit)\b", c["name"])
        return (group_order.index(c["group"]), int(num.group(1)) if num else 10 ** 6,
                c["_order"], c["name"])
    return key


def selftest():
    checks = [
        (clean_choice("(JB Pritzker (Christian Mitchell"), "JB Pritzker & Christian Mitchell"),
        (clean_choice("(Darren Bailey (Aaron B, Del Mar"), "Darren Bailey & Aaron B, Del Mar"),
        (clean_choice("WRITE-IN"), None), (clean_choice("No Candidate"), ""),
        (clean_choice("YES"), "Yes"),
        (match_choice("Darren Bailey & Arron B. Del Mar",
                      ["Darren Bailey & Aaron B. Del Mar", "JB Pritzker & Christian Mitchell"]), 0),
        (match_choice("JB Pritzker & Christian Mithcell",
                      ["Darren Bailey & Aaron B. Del Mar", "JB Pritzker & Christian Mitchell"]), 1),
        (match_choice("Chris Gant", ["Chris Gant (Write-in)", "Don Tracy"]), 0),
        (match_choice("Somebody Else", ["Don Tracy"]), None),
        (match_choice("Pritzker & Mitchell", ["Darren Bailey & Aaron B. Del Mar", "JB Pritzker & Christian Mitchell"]), 1),
        (match_choice("JB Pritzker", ["Darren Bailey & Aaron B. Del Mar", "JB Pritzker & Christian Mitchell"]), 1),
        (match_choice("Bailey & Del Mar", ["Darren Bailey & Aaron B. Del Mar", "JB Pritzker & Christian Mitchell"]), 0),
        (match_choice("Mitchell", ["Darren Bailey & Aaron B. Del Mar", "JB Pritzker & Christian Mitchell"]), None),
        (result_to_map("henry", "ALBA", ["Alba 1", "Andover 1"]), "Alba 1"),
        (result_to_map("wayne", "GOLDENGATE", ["GOLDEN GATE"]), "GOLDEN GATE"),
        (result_to_map("wayne", "MASSILON", ["Massillon"]), "Massillon"),
        (result_to_map("randolph", "PRAIRIE DU ROCHER", ["PR DU ROCHER"]), "PR DU ROCHER"),
        (result_to_map("kane", "AU0001", ["AU01", "AU10"]), "AU01"),
        (result_to_map("kane", "AU0010", ["AU01", "AU10"]), "AU10"),
        (classify("FOR REPRESENTATIVE IN THE GENERAL ASSEMBLY SEVENTIETH-FOURTH REPRESENTATIVE DISTRICT",
                  "74TH REPRESENTATIVE DIST", "DeKalb", 1, ["A", "B"])[2], "State Representative, 74th District"),
        (classify("FOR COUNTY BOARD MEMBER DISTRICT 5 (To Serve an Unexpired 2-Year Term)",
                  "COUNTY BOARD DIST 5", "DeKalb", 1, ["A", "B"])[2],
         "DeKalb County Board, District 5 (unexpired 2-year term)"),
        (classify("FOR COUNTY BOARD - AT LARGE", "COUNTY BOARD", "Pike", 5, ["A"])[2], "Pike County Board, at large"),
        (classify("FOR TREASURER", "STATE OF ILLINOIS", "DeKalb", 1, ["A"])[2], "Treasurer, State of Illinois"),
        (classify("FOR COUNTY SHERIFF", "COUNTY", "Lake", 1, ["A"])[2], "Sheriff, Lake County"),
        (classify("FOR CHAIRPERSON OF THE COUNTY BOARD", "COUNTY", "DuPage", 1, ["A"])[:3],
         ("county", "Chairperson of the County Board, DuPage County", "Chairperson of the County Board, DuPage County")),
        (classify("FOREST PRESERVE COMMISSIONER DISTRICT 2", "FOREST PRESERVE", "DuPage", 1, ["A"])[2],
         "Commissioner, DuPage County Forest Preserve District, District 2"),
        (classify("FOR REGIONAL SUPERINTENDENT OF SCHOOLS (DeWITT, LIVINGSTON, LOGAN and McLEAN Counties)", "",
                  "Sangamon", 1, ["A"])[1:3],
         ("counties DEWITT,LIVINGSTON,LOGAN,MCLEAN",
          "Regional Superintendent of Schools (DeWitt, Livingston, Logan and McLean Counties)")),
        (classify("FOR COUNTY TREASURER", "DEKALB COUNTY", "DeKalb", 1, ["A"])[2], "Treasurer, DeKalb County"),
        (classify("FOR STATE'S ATTORNEY (TO SERVE AN UNEXPIRED 2-YEAR TERM)", "WAYNE COUNTY", "Wayne", 1,
                  ["A"])[2], "State's Attorney, Wayne County (unexpired 2-year term)"),
        (classify("SHALL EACH OF THE PERSONS LISTED BE RETAINED IN OFFICE AS JUDGE OF THE APPELLATE COURT, "
                  "FIFTH JUDICIAL DISTRICT? JOHN B. BARBERIS, JR.", "5TH JUDICIAL DISTRICT", "Franklin", 1,
                  ["YES", "NO"])[1],
         classify("Shall Judge John B. Barberis, Jr. be retained in office as Judge of the Fifth Appellate Court?",
                  "5TH JUDICIAL DISTRICT", "Wayne", 1, ["YES", "NO"])[1]),
        (classify("FOR JUDGE OF THE APPELLATE COURT FIFTH JUDICIAL DISTRICT (To fill the vacancy of the Hon. "
                  "Thomas M. Welch)", "5TH JUDICIAL DISTRICT", "Franklin", 1, ["A"])[1],
         classify("FOR JUDGE OF THE APPELLATE COURT FIFTH JUDICIAL DISTRICT (To fill the vacancy of the Hon.Thomas "
                  "M. Welch)", "5TH JUDICAL DISTRICT", "Randolph", 1, ["A"])[1]),
        (classify("FOR REGIONAL SUPERINTENDENT OF SCHOOLS (DEKALB COUNTY)", "ESR-16 (DEKALB)", "DeKalb", 1,
                  ["A"])[3]["counties"], ["DeKalb"]),
        (beyond_for("regional", {"counties": ["Dekalb"]}, "dekalb", "DeKalb"), False),
        (beyond_for("retention", {"court": "circuit", "num": 16}, "kane", "Kane"), False),
        (classify("FOR SECRETARY OF STATE", "STATE OF ILLINOIS", "Pike", 1, ["A"])[2],
         "Secretary of State, State of Illinois"),
        (classify("FOR COUNTY CLERK AND RECORDER", "HENRY COUNTY", "Henry", 1, ["A"])[2], "Clerk and Recorder, Henry County"),
        (classify("CIRCUIT COURT JUDGE JOSEPH M. GRADY SEEKING RETENTION IN OFFICE", "", "Kane", 1, ["Yes", "No"])[2],
         "Joseph M. Grady (Circuit Court, 16th Circuit)"),
        (classify("DEKALB COUNTY FOR REGIONAL SUPERINTENDENT OF SCHOOLS", "", "Kane", 1, ["A"])[1],
         classify("FOR REGIONAL SUPERINTENDENT OF SCHOOLS (DEKALB COUNTY)", "ESR-16 (DEKALB)", "DeKalb", 1, ["A"])[1]),
        (spelled_ordinal("SEVENTY-SEVENTH REPRESENTATIVE DISTRICT"), 77),
        (spelled_ordinal("FORTY-FIRST LEGISLATIVE"), 41), (spelled_ordinal("SEVENTH REPRESENTATIVE"), 7),
        (spelled_ordinal("ONE HUNDRED EIGHTEENTH"), 118), (spelled_ordinal("FIFTIETH"), 50),
        (spelled_ordinal("SEVENTIETH-FOURTH"), 74), (spelled_ordinal("EIGHTEENTH JUDICIAL"), 18),
        (result_to_map("dupage", "Addison 001", ["Addison 1", "Addison 10"]), "Addison 1"),
        (result_to_map("sangamon", "LOAMI", ["LOAMI 001", "LOAMI 2"]), None),
        (result_to_map("sangamon", "MAXWELL", ["MAXWELL 001"]), "MAXWELL 001"),
        (result_to_map("bloomington", "PRECINCT 7", ["City of Bloomington 7"]), "City of Bloomington 7"),
        (clean_choice("No Candidate (REP)"), ""), (clean_choice("Rejected write-ins"), False),
        (clean_choice("(JB Pritzker (Christian Mitchell (DEM)"), "JB Pritzker & Christian Mitchell"),
    ]
    bad = [(got, want) for got, want in checks if got != want]
    for got, want in bad:
        print("il-county-election-results selftest: got %r, want %r" % (got, want))
    try:
        classify("FOR DOGCATCHER", "SOMEWHERE", "Pike", 1, ["A"])
        bad.append(("unknown contest", "accepted"))
    except CountyError:
        pass
    if bad:
        raise SystemExit(1)
    print("il-county-election-results selftest: OK — %d checks and 1 refusal" % len(checks))


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        selftest()
    else:
        raise SystemExit("usage: build_il_county_election_results.py --selftest (the Chicago builder's "
                         "--counties option is what runs it)")
