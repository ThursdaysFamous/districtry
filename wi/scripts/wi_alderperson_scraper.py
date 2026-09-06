#!/usr/bin/env python3
"""
Scrape the alderperson rosters for the Wisconsin municipalities whose
aldermanic districts the statewide dissolve ships AND whose rosters have a
verified open route — six measured 2026-08-26, twelve more 2026-09-05.
Stage 1 of the pair; build_wi_alderperson_roster.py writes
data/app/wi-alderpersons.json.

THE FIRST SIX, each with its route and its measured trap:

  Milwaukee (15)  — Legistar (webapi.legistar.com), the Common Council's own
                    system of record: OfficeRecordTitle carries the district
                    ("3rd District", cross-checked against OfficeRecordSort)
                    and First/Last carry the name. NEVER OfficeRecordFullName,
                    which is "ALD. SURNAME".
                    THE CITY'S GIS LAYER WAS THE SOURCE UNTIL 2026-09-05 and is
                    not fetched any more: milwaukeemaps.milwaukee.gov publishes
                    `User-agent: * / Disallow: /`. The city's open-data CKAN
                    shapefile corroborates per district where it answers, and
                    is not required to. Current membership is filtered
                    client-side against today's date.
                    THAT MOVE COST ONE SUFFIX AND IT IS NOT PUT BACK BY HAND:
                    the retired GIS layer spelled district 15 "Russell W
                    Stamper, II" and Legistar — the Council's own system of
                    record — carries First "Russell W." / Last "Stamper", with
                    no suffix field anywhere in the record (Chambers Jr. keeps
                    his, inside the LAST name). Restoring the II would mean
                    typing a name this project cannot source, so the shipped
                    spelling is the Council's own.
  Madison (20)    — the council index page's per-alder links. THE INDEX'S
                    FLAT TEXT PAIRING IS A TRAP: District 1 is vacant, so a
                    flattened read pairs every alder with the district ABOVE
                    their real one (measured: "District 1 / Alder Ochowicz"
                    on the flat page; Ochowicz's own page is District 2).
                    The district comes from each alder's own /council/
                    districtN page — its H1 states "District N - Alder
                    SURNAME" or "District N - Vacant" — and the seat e-mail
                    districtN@cityofmadison.com rides the page.
  Green Bay (12)  — the city's staff directory, parsed per <li> entry
                    (never flattened: the responsive layout prints each
                    title twice). Name, real mailto, phone, profile URL.
                    One entry measures a display-name/e-mail nickname split
                    ("Bill Morgan" / mailto Jim... no — William) — the
                    display name ships.
  Kenosha (17)    — the city GIS's Districts_ElectedRepresentation layer
                    (REP_AREA='D' rows carry REPRESNTTV; each district
                    appears twice, once named and once 'N/A' — both facts
                    gated). kenosha.org itself is Cloudflare-challenged, so
                    the currency witness is the COUNTY's certified April
                    2026 spring canvass (kenoshacountywi.gov, open): all 17
                    alderperson contests, positionally parsed — candidate
                    names are CENTERED vertical column headers, so stacks
                    cluster by column CENTER (clustering by left edge reads
                    the winner out of the wrong column; measured), and the
                    Totals row's first k numbers are the k candidates'
                    votes. Every GIS name must match its district's
                    certified winner.
  Racine (15)     — the city's alderman index, "District #N – Alderman
                    NAME" one line per district, plus each district's page
                    link (the slugs are inconsistent — "district-1" and
                    "02-district" both live — so the link is captured from
                    the line, never composed).
  Waukesha (15)   — the common-council page's per-district blocks:
                    "Aldermanic District N" / "Wards …" / NAME / phone /
                    seat e-mail (alddistN@waukesha-wi.gov — the seat's, so
                    contact survives turnover).

THE TWELVE OF 2026-09-05 — Stevens Point, Menomonie, Manitowoc, Sheboygan,
Superior, Portage, Viroqua, Menasha, Howard, Tomah, Eau Claire and Appleton — carry
their route and their traps on each scrape_* function below, under the sweep
that found them. Three of those traps are worth naming here because they are
the ones that ship a WRONG answer rather than none: Manitowoc's anchors carry
a title= attribute naming the PREVIOUS alderperson on two rows; Menasha's
District 1 cell holds a staff member's mailto that is not the alderperson's;
and Menasha and Portage both publish their members' HOME ADDRESSES, which
never ship, for anybody, anywhere in this fleet.

APPLETON WAS HELD OUT UNTIL 2026-09-05 for exactly one reason and it was the
right one: its roster page has been readable since 2026-08-26 and its GEOMETRY
could not be drawn, so there was no card for the names to ride. Outagamie
County still files all 50 of its Appleton wards uncoded; what changed is that
the CITY CLERK's own polling-locations page turned out to state the
composition, and build_wi_aldermanic_districts.py now composes the fifteen
districts from it under three independent witnesses and a second edition of
one of them. A roster and the boundary it rides ship together or not at all.
"""

import html as H
import io
import json
import os
import re
import ssl
import struct
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
import zipfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(SCRIPT_DIR, ".cache")
DEFAULT_OUT = os.path.join(CACHE_DIR, "wi_alderpersons_raw.json")

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

# REMOVED 2026-09-05: milwaukeemaps.milwaukee.gov/arcgis/rest/services/election
# /alderman/... was this file's primary Milwaukee source, and that host publishes
# `User-agent: * / Disallow: /`. It is not re-added under another name or agent;
# scrape_milwaukee() reads Legistar, which it was already fetching.
MKE_CKAN_ZIP = ("https://data.milwaukee.gov/dataset/1301738f-4b4a-4f73-bbaa-a4cac069e371"
                "/resource/4b68b244-779e-406f-9d94-7fb85a764496/download/alderman.zip")
MKE_LEGISTAR = ("https://webapi.legistar.com/v1/milwaukee/officerecords"
                "?$filter=OfficeRecordBodyId%20eq%201&$top=1000")
MADISON_INDEX = "https://www.cityofmadison.com/council/council-members"
MADISON_DISTRICT = "https://www.cityofmadison.com/council/district%d"
GREEN_BAY_DIR = "https://www.greenbaywi.gov/m/directory"
KENOSHA_GIS = ("https://gis-city.kenosha.org/server/rest/services/Organizational_Layers"
               "/Districts_ElectedRepresentation/FeatureServer/150/query"
               "?where=REP_AREA%3D%27D%27&outFields=DIST_NO,REPRESNTTV"
               "&returnGeometry=false&f=json&resultRecordCount=100")
KENOSHA_CANVASS = ("https://www.kenoshacountywi.gov/DocumentCenter/View/31064"
                   "/OFFICIAL-CANVASSED-RESULTS")
RACINE_INDEX = ("https://cityofracinewi.gov/government/city-leadership"
                "/common-council/cityalderman/")
WAUKESHA_INDEX = "https://www.waukesha-wi.gov/about_the_common_council/index.php"

# ---------------------------------------------------------------------------
# THE TWELVE ADDED 2026-09-05, each hand-read from its own page before a line of
# parser was written. They came out of a sweep of all 149 unrostered districted
# municipalities: home page (robots.txt honoured first), then up to two hops of
# council-ish links, scoring how many of the municipality's districts a page
# pairs with a person. The sweep is a TRIAGE — it points at pages worth reading;
# nothing below ships from its score.
#
# WHAT THE SWEEP MEASURED, over all 149:
#
#     32  a page pairing every district with a name, read automatically
#     14  the same, partially
#     67  home page readable, no such pairing found
#     17  the host publishes `User-agent: * / Disallow: /`
#     15  the host answers HTTP 403 to this client
#      3  a network error or an HTTP 503
#      1  no municipal website in the Elections Commission's clerk file (Hurley)
#
# So the record this replaces — "no bulk source exists", which is true — was
# silent about the thing that actually decides each city, and 32 municipalities
# were publishing exactly what the gap said was wanted. The 17 blanket Disallows
# are the finding worth naming: Baraboo, Cudahy, Delavan, Elroy, Marion,
# Marshfield, Mauston, Merrill, Prairie du Chien, Princeton, Reedsburg, Rice
# Lake, Ripon, St Croix Falls, St Francis, Tomahawk, Westfield. Those are shut,
# not unexamined, and nothing here renames a user agent to get past one.
#
# TEN OF THE TWELVE BELOW CAME OUT OF THAT 32, AND MENOMONIE DID NOT — its
# council page pairs every seat with a name and the triage scored it 0, because
# the crawl never reached the page inside its six-link budget. The sweep
# UNDER-reports, which is the right direction for a triage and the reason the
# 67 "no pairing found" is a floor rather than a verdict.
#
# THE TWENTY-TWO FULL MATCHES the sweep found. FIVE WERE BUILT on 2026-09-05
# evening (New Berlin, Sturgeon Bay, Altoona, Eagle River, Germantown — 28
# seats) and FIVE MORE WERE MEASURED SHUT that same evening, which is the more
# useful half:
#
#   ALGOMA, DODGEVILLE, OCONOMOWOC and HORICON each seat TWO alderpersons per
#   district on staggered terms — Dodgeville's district 1 is Shaun Sersch
#   (2025-2027) AND Roxanne Reynolds-Lair (2026-2028), and so on. The roster
#   schema is members[district] -> ONE member, so naming either would conceal
#   the other. Shut on the SCHEMA, not on the source: representing them needs
#   a schema and a card that hold a list. THE SWEEP COULD NOT HAVE SEEN THIS —
#   it scored district-to-name PAIRINGS, and a page that pairs each district
#   twice scores as a full match.
#
#   WAUPACA's page numbers its districts 1-5 while LTSB keys its geometry
#   41-45. Nothing read here witnesses the correspondence, and a wrong offset
#   moves every name one seat, so it is not guessed.
#
# ALL 22 ARE MEASURED AS OF 2026-09-06. Six ship one member per district (the
# five above plus New Lisbon); FIFTEEN seat more than one, and Wisconsin Dells
# is a probable sixteenth. The last three read — Black River Falls (two per
# ward, 8 over 4; its labels are uppercase WARD N, which a case-sensitive
# pattern misses), Neenah (three per district, 9 over 3) and Wautoma (UNEVEN at
# one, three and two, 6 over 3) — are all multi-member. WAUTOMA SETTLES THE
# DESIGN QUESTION: a two-slot schema would not carry it; these cities need a
# genuine LIST per district. Wautoma also prints home addresses beside every
# name, which are never read.
#
# The remaining twelve, with the page the sweep scored, so the next pass starts
# from a measurement instead of repeating this one. THEIR SEAT VOCABULARY WAS
# MEASURED 2026-09-05: seven number seats by WARD (the Viroqua shape, needing
# the live LTSB ward-is-district witness) — Cumberland, Hillsboro, Nekoosa,
# New Lisbon, Westby, Greenwood, Montreal; Wautoma writes "Dist. N" and
# Wisconsin Dells an ordinal "Nth District"; Black River Falls, Neenah and
# New Holstein pair by neither, and want a read before a regex:
#
#   Waupaca           C 5  https://cityofwaupaca.org/government/mayor-city-council/
#   Algoma            C 4  https://www.algomacity.org/government/city_council.php
#   Horicon           C 3  https://www.horiconwi.gov/185/Elected-Officials
#   Black River Falls C 4  https://blackriverfallswi.gov/common-council-committee-of-the-whole
#   Cumberland        C 4  https://cityofcumberland.net/city-council
#   Dodgeville        C 4  https://www.cityofdodgeville.com/council
#   Hillsboro         C 4  https://www.hillsborowi.com/mayor-and-council
#   Nekoosa           C 4  https://cityofnekoosa.org/city-council
#   New Holstein      C 4  https://cityofnewholstein.org/elected-officials/
#   New Lisbon        C 4  https://cityofnewlisbon.com/common-council
#   Oconomowoc        C 4  https://oconomowoc-wi.gov/225/Common-Council
#   Horicon           C 3  https://www.horiconwi.gov/185/Elected-Officials
#   Neenah            C 3  https://www.ci.neenah.wi.us/common-council/
#   Wautoma           C 3  http://www.cityofwautoma.com/common-council
#   Westby            C 3  https://www.cityofwestby.org/westby-city-council
#   Wisconsin Dells   C 3  https://www.citywd.org/departments/city-government
#   Greenwood         C 2  https://cityofgreenwood.wi.gov/city-council
#   Montreal          C 2  https://montrealwis.com/departments/city-council/
#
# These are ADDRESSES THIS MODULE DOES NOT FETCH — a queue, deliberately in a
# comment rather than in an upper-case table, because validate_robots.py reads
# upper-case attributes as scheduled fetches and would report policies for
# requests nobody makes.
LTSB_WARDS = ("https://services1.arcgis.com/FDsAtKBk8Hy4cAH0/arcgis/rest"
              "/services/WI_Municipal_Wards_Current/FeatureServer/0/query")
STEVENS_POINT_DIR = "https://stevenspoint.com/Directory.aspx?DID=23"
MENOMONIE_INDEX = "https://www.menomonie-wi.gov/248/City-Council"
MANITOWOC_INDEX = "https://www.manitowoc.org/78/Meet-Your-Alderperson"
SHEBOYGAN_INDEX = "https://www.sheboyganwi.gov/395/Common-Council"
# www.ci.superior.wi.us answers, and 301s to this host; the redirect target is
# what ships so a reader clicks the address the city actually serves.
SUPERIOR_INDEX = "https://www.superiorwi.gov/697/City-Councilor-Information"
PORTAGE_INDEX = "https://www.portagewi.gov/mayor-and-council"
# http:// 301s here, the same shape as Superior's host; the redirect target is
# what ships so a reader clicks the address the city actually serves.
VIROQUA_INDEX = ("https://viroqua-wisconsin.com/government"
                 "/city_council_and_committees.php")
MENASHA_INDEX = ("https://www.menashawi.gov/residents/government"
                 "/common_council/index.php")
HOWARD_INDEX = ("https://www.villageofhoward.com/208"
                "/Village-President-Board-of-Trustees")
TOMAH_INDEX = "https://www.tomahwi.gov/citycouncil"
EAU_CLAIRE_INDEX = "https://www.eauclairewi.gov/310/City-Council"

# ---- the tranche of 2026-09-05 evening, from the 22 the sweep had measured ----
# FIVE constants, for the five cities actually fetched. Algoma, Dodgeville,
# Oconomowoc and Horicon were built and then withdrawn (two members per
# district, see below), and their addresses go back to the queue comment
# rather than staying here: validate_robots.py reads an upper-case module
# attribute as a SCHEDULED FETCH and would report policies for requests this
# module no longer makes.
# Each address moves from the queue comment above into a constant HERE in the
# same change that starts fetching it, never before: validate_robots.py reads
# upper-case module attributes as scheduled fetches and would otherwise report
# policies for requests nobody makes. robots.txt was read for ALL TWENTY-TWO
# candidate hosts before any page fetch, not just the five kept — none
# carries a Disallow reaching these paths.
NEW_LISBON_INDEX = "https://cityofnewlisbon.com/common-council"
NEW_BERLIN_INDEX = "https://www.newberlinwi.gov/"
STURGEON_BAY_INDEX = ("https://www.sturgeonbaywi.org/government/"
                      "city_council/index.php")
ALTOONA_INDEX = "https://www.altoonawi.gov/government/elected_officials.php"
EAGLE_RIVER_INDEX = "https://eagleriverwi.gov/city-government/elected-officials/"
GERMANTOWN_INDEX = "https://www.germantownwi.gov/299/Village-Board"

APPLETON_INDEX = "https://www.appletonwi.gov/government/common_council.php"

ORDINALS = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
            "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
            "eleventh": 11, "twelfth": 12, "thirteenth": 13, "fourteenth": 14,
            "fifteenth": 15, "sixteenth": 16, "seventeenth": 17,
            "eighteenth": 18, "nineteenth": 19, "twentieth": 20}

# Districts where the certified April 2026 canvass OVERRIDES the city GIS,
# each pinned only after its story was read. The pin is self-retiring twice
# over: it fails if the canvass stops naming this winner, and it fails the
# day the GIS catches up (remove it then).
# RETIRED 2026-09-03, EXACTLY AS THIS BLOCK'S OWN COMMENT INSTRUCTS. District
# 14's pin existed because the GIS still named Kenny Harper, who won in April
# 2024 and did not seek re-election; Daniel Prozanski won the certified April
# 2026 contest 913 votes to write-ins' 17. The city's layer now names Prozanski
# itself, so there is no longer a disagreement to override and the card ships
# the city's own current spelling with no override note — which is the whole
# point of a self-retiring pin.
#
# IT DID NOT SELF-RETIRE, AND THAT WAS A REAL DEFECT rather than an oversight:
# the loop below tested the GIS against the canvass FIRST and `continue`d on a
# match, so the "the GIS now agrees — remove the pin" guard sat behind a branch
# that could no longer be reached. The pin had become dead code announcing
# nothing. The pin check now runs BEFORE that test, so the next one retires
# itself loudly on the day it should.
KENOSHA_CANVASS_WINS = {}

CITIES = {  # COUSUBFP -> (name, seats)
    "53000": ("Milwaukee", 15),
    "48000": ("Madison", 20),
    "31000": ("Green Bay", 12),
    "39225": ("Kenosha", 17),
    "66000": ("Racine", 15),
    "84250": ("Waukesha", 15),
    "77200": ("Stevens Point", 11),
    "51025": ("Menomonie", 11),
    "48500": ("Manitowoc", 10),
    "72975": ("Sheboygan", 10),
    "78650": ("Superior", 10),
    "64100": ("Portage", 9),
    "82925": ("Viroqua", 9),
    "50825": ("Menasha", 8),
    "35950": ("Howard", 8),
    "80075": ("Tomah", 8),
    "22300": ("Eau Claire", 5),
    "02375": ("Appleton", 15),
}


def fetch(url, binary=False, tries=3, timeout=60):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout,
                                        context=ssl.create_default_context()) as r:
                data = r.read()
            return data if binary else data.decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001 — retried, then re-raised
            last = e
            time.sleep(2 * (i + 1))
    raise last


def fold(name):
    """First + last alphabetic token, accent-stripped — the fleet's person
    fold: middle initials, suffixes and diacritics never read as different
    people; a genuinely different first or last name still does."""
    s = unicodedata.normalize("NFKD", str(name))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    toks = [t for t in re.split(r"[^a-z]+", s) if len(t) > 1 and t not in
            ("jr", "sr", "ii", "iii", "iv")]
    return (toks[0] + "|" + toks[-1]) if toks else ""


def fold_set(name):
    """Unordered token fold, for a source that prints names surname-first:
    the Kenosha canvass's vertical column headers reassemble in reading
    order ('LaMacchia, Rocco Sr. J.'), so ordered first|last comparison
    reads a reversal as a different person. The token SET doesn't care."""
    s = unicodedata.normalize("NFKD", str(name))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return frozenset(t for t in re.split(r"[^a-z]+", s) if len(t) > 1 and t not in
                     ("jr", "sr", "ii", "iii", "iv"))


def strip_tags(html):
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", html, flags=re.S)
    t = re.sub(r"<[^>]+>", "\n", t)
    return [l.strip() for l in H.unescape(t).split("\n") if l.strip()]


# ---------------------------------------------------------------- Milwaukee
def read_dbf(data):
    n_rec = struct.unpack("<I", data[4:8])[0]
    hdr_len = struct.unpack("<H", data[8:10])[0]
    rec_len = struct.unpack("<H", data[10:12])[0]
    fields = []
    off = 32
    while data[off] != 0x0D:
        name = data[off:off + 11].split(b"\x00")[0].decode()
        fields.append((name, data[off + 16]))
        off += 32
    rows = []
    pos = hdr_len
    for _ in range(n_rec):
        rec = data[pos:pos + rec_len]
        pos += rec_len
        o = 1
        row = {}
        for name, flen in fields:
            row[name] = rec[o:o + flen].decode("latin1").strip()
            o += flen
        rows.append(row)
    return rows


def scrape_milwaukee():
    """Milwaukee's 15 alderpersons, from Legistar — which was already the witness.

    THE OLD PRIMARY WAS A HOST THAT ASKS NOT TO BE CRAWLED. milwaukeemaps.
    milwaukee.gov publishes

        User-agent: Googlebot
        Allow: /
        User-agent: *
        Disallow: /

    and this function fetched its alderman layer every week, six times over with
    backoff, under a comment calling it "the measured flaky host". It is not
    flaky; it is asking. wi/scripts/validate_robots.py did not cover this module
    until 2026-09-05, which is the whole reason a blanket Disallow went unread
    for as long as it did.

    NOTHING IS LOST AND NO SOURCE IS ADDED. Legistar was already fetched on
    every run as the currency witness, and it carries the district as well as
    the name: OfficeRecordTitle is "3rd District", corroborated by
    OfficeRecordSort. Measured 2026-09-05 against the shipped roster: 15 of 15
    districts and 15 of 15 surnames. So the two fetches this function makes are
    unchanged in number — the ROLES are swapped, and the disallowed one is gone.

    SIX ROWS CHANGED SPELLING ON THE FIRST REBUILD, NOT ONE. An earlier version
    of this paragraph said "one suffix difference", which was the one that
    LOSES something and not the count. The GIS spelled middle names out and
    Legistar abbreviates or omits them: D01 "Andrea M Pratt" -> "Andrea Pratt",
    D02 "Mark Chambers, Jr" -> "Mark Chambers Jr.", D06 "Milele A Coggs" ->
    "Milele A. Coggs", D10 "Sharlen P Moore" -> "Sharlen Moore", D12 "Jose G
    Perez" -> "Jose Perez", D15 "Russell W Stamper, II" -> "Russell W. Stamper".
    Same six people, the Council's own styling. Only D15 loses a name part
    Legistar does not carry at all — there is no suffix field anywhere in the
    record (Chambers keeps his inside the LAST name) — and it is NOT typed back
    in by hand, because that would be a name this project cannot source.

    The CKAN shapefile stays as corroboration rather than as a fallback: it is
    the city's own open-data portal, its robots.txt permits the path, and where
    it answers its districts must agree. It is NOT required, because a host
    that declines one client on one day must not be able to fail a build whose
    data is already sound.
    """
    today = time.strftime("%Y-%m-%d")
    recs = json.loads(fetch(MKE_LEGISTAR))
    members, current = {}, set()
    for r in recs:
        start = (r.get("OfficeRecordStartDate") or "")[:10]
        end = (r.get("OfficeRecordEndDate") or "9999")[:10]
        if not (start <= today <= end):
            continue
        # NEVER OfficeRecordFullName — that column is "ALD. SURNAME" (measured),
        # so the name is built from the First/Last columns.
        full = ((r.get("OfficeRecordFirstName") or "") + " " +
                (r.get("OfficeRecordLastName") or "")).strip()
        if full:
            current.add(fold(full))
        m = re.match(r"\s*(\d+)(?:st|nd|rd|th)\s+District\s*$",
                     r.get("OfficeRecordTitle") or "", re.I)
        if not (m and full):
            continue
        num = int(m.group(1))
        # THE TITLE AND THE SORT COLUMN MUST AGREE. Two fields on the same
        # record naming the same district is the cheapest witness available,
        # and a Legistar body whose Sort stopped tracking the district is
        # exactly the drift that would put a name under the wrong ward.
        sort = r.get("OfficeRecordSort")
        if isinstance(sort, int) and sort != num:
            raise SystemExit("milwaukee: Legistar title %r says district %d but "
                             "OfficeRecordSort says %d — the two disagree, so "
                             "neither is trusted" % (r.get("OfficeRecordTitle"),
                                                     num, sort))
        members["%02d" % num] = {"name": full}
    if len(members) != 15:
        raise SystemExit("milwaukee: Legistar names %d of 15 districts among %d "
                         "current COMMON COUNCIL records" % (len(members),
                                                             len(current)))
    source = MKE_LEGISTAR

    # Corroboration, not a dependency: where the city's open-data shapefile
    # answers, its districts must agree with Legistar's.
    # ONLY THE FETCH IS ALLOWED TO FAIL QUIETLY. A parse error inside this try
    # would have been reported as "did not answer", which is a different fact
    # about a different party — so the download is the only thing it covers.
    try:
        blob = fetch(MKE_CKAN_ZIP, binary=True)
    except Exception as exc:  # noqa: BLE001 — a witness that declines is not a failure
        print("milwaukee: the CKAN shapefile did not answer (%s); Legistar's %d "
              "districts ship uncorroborated this run"
              % (type(exc).__name__, len(members)), file=sys.stderr)
    else:
        z = zipfile.ZipFile(io.BytesIO(blob))
        dbf = next(n for n in z.namelist() if n.lower().endswith(".dbf"))
        ckan = {"%02d" % int(row["DISTRICT"]): row["ALDERPERSO"].strip()
                for row in read_dbf(z.read(dbf))}
        # PER DISTRICT, NOT MEMBERSHIP. Asking only whether CKAN's name is
        # somewhere in the current council would pass a shapefile that had every
        # alderperson right and every district wrong — which is precisely the
        # failure a second source is here to catch.
        disagree = sorted(d for d, name in ckan.items()
                          if d in members and fold(name) != fold(members[d]["name"]))
        if disagree:
            raise SystemExit(
                "milwaukee: CKAN and Legistar name different people for district(s) "
                "%s — %s — so one of the two is stale and neither is trusted"
                % (disagree, ["%s: CKAN %r vs Legistar %r"
                              % (d, ckan[d], members[d]["name"]) for d in disagree]))
        print("milwaukee: CKAN corroborates %d of %d districts by name"
              % (sum(1 for d in ckan if d in members), len(members)),
              file=sys.stderr)
    return members, source


# ------------------------------------------------------------------ Madison
def scrape_madison():
    index = fetch(MADISON_INDEX)
    by_href = {}
    for m in re.finditer(r'href="(?:https://www\.cityofmadison\.com)?/council/district(\d+)"'
                         r'[^>]*>\s*Alder\s+([^<]+)<', index):
        # UNESCAPE. The index writes an apostrophe as `&#039;`, and D16 shipped
        # the literal "Sean O&#039;Brien" from 2026-08-26 to 2026-09-05 because
        # nothing here decoded it and the card renders through textContent, which
        # is exactly right for safety and does not undo an entity. The surname
        # gate below never caught it either: fold() drops punctuation, so
        # "O&#039;Brien" and "O'Brien" both fold to "brien".
        by_href[int(m.group(1))] = " ".join(H.unescape(m.group(2)).split())
    if not (17 <= len(by_href) <= 20):
        raise SystemExit("madison index links %d alder districts (expected ~19-20 "
                         "with vacancies) — the page shape moved" % len(by_href))
    members = {}
    vacant = []
    for n in range(1, 21):
        page = fetch(MADISON_DISTRICT % n)
        h1 = re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S)
        head = H.unescape(re.sub(r"<[^>]+>", "", h1.group(1))).strip() if h1 else ""
        if not head.startswith("District %d" % n):
            raise SystemExit("madison district page %d headlines %r" % (n, head))
        if "Vacant" in head:
            vacant.append(n)
            continue
        sur = re.sub(r"^District %d\s*-\s*Alder\s*" % n, "", head).strip()
        name = by_href.get(n)
        if not name or fold(name).split("|")[-1] != fold("x " + sur).split("|")[-1]:
            raise SystemExit("madison D%d: index name %r does not carry the page's "
                             "surname %r — the index/href pairing moved" % (n, name, sur))
        entry = {"name": name, "url": MADISON_DISTRICT % n}
        m = re.search(r'mailto:(district%d@cityofmadison\.com)' % n, page)
        if m:
            entry["email"] = m.group(1)
        members["%02d" % n] = entry
    if len(members) + len(vacant) != 20:
        raise SystemExit("madison: %d named + %d vacant != 20" % (len(members), len(vacant)))
    if len(members) < 17:
        raise SystemExit("madison names only %d of 20 districts" % len(members))
    return members, MADISON_INDEX, vacant


# ---------------------------------------------------------------- Green Bay
def scrape_green_bay():
    page = fetch(GREEN_BAY_DIR)
    members = {}
    # split on the ENTRY container class, never a bare <li>: each entry nests
    # a <ul><li> department list, so a bare-<li> split cuts the entry before
    # its e-mail and phone column (measured — the first draft shipped twelve
    # names with no contact at all)
    for li in re.split(r'<li class="list-group-item', page)[1:]:
        t = re.search(r"District\s+(\d+)\s+Alderperson", li)
        if not t:
            continue
        n = int(t.group(1))
        nm = re.search(r'href="(/m/directory/employee\?eid=\d+)"[^>]*>\s*([^<]+?)\s*<', li)
        if not nm:
            continue
        entry = {"name": " ".join(nm.group(2).split()),
                 "url": "https://www.greenbaywi.gov" + nm.group(1)}
        em = re.search(r'mailto:([^"?]+)"', li)
        if em:
            entry["email"] = em.group(1).strip()
        ph = re.search(r'href="tel:([^",]+)', li)
        if ph:
            entry["phone"] = ph.group(1).strip()
        key = "%02d" % n
        if key in members and members[key]["name"] != entry["name"]:
            raise SystemExit("green bay lists two names for district %d" % n)
        members[key] = entry
    if len(members) != 12:
        raise SystemExit("green bay names %d of 12 districts" % len(members))
    return members, GREEN_BAY_DIR


# ------------------------------------------------------------------ Kenosha
def kenosha_canvass_winners(pdf_path):
    """Positional parse of the county's certified canvass: per alderperson
    contest, candidate columns are centered vertical stacks; the Totals
    row's first k numbers are the k candidates' votes."""
    import pdfplumber
    BOIL = {"VOTE", "FOR", "of", "Precincts", "Reporting", "Totals", "Cast",
            "Total", "Votes", "Overvotes", "Undervotes", "Contest", "Write-in"}
    wins = {}
    with pdfplumber.open(pdf_path) as pdf:
        for pg in pdf.pages:
            words = pg.extract_words()
            titles = []
            for i, w in enumerate(words):
                if (w["text"] == "Alderperson" and i + 2 < len(words)
                        and words[i + 1]["text"] == "District"
                        and re.match(r"^\d+$", words[i + 2]["text"])):
                    titles.append({"n": int(words[i + 2]["text"]), "x0": w["x0"]})
            if not titles:
                continue
            votes = sorted((w for i, w in enumerate(words) if w["text"] == "VOTE"
                            and i + 1 < len(words) and words[i + 1]["text"] == "FOR"),
                           key=lambda w: w["x0"])
            reps = [w for w in words if w["text"] == "Reporting"]
            units = [w for w in words if w["text"] in ("Town", "Village", "City")]
            tots = [w for w in words if w["text"] == "Totals"]
            if not (votes and reps and units and tots):
                continue
            h_top = max(r["top"] for r in reps) + 2
            unit_tops = [u["top"] for u in units if u["top"] > h_top]
            if not unit_tops:
                continue
            h_bot = min(unit_tops) - 2
            trow = max(tots, key=lambda w: w["top"])
            hw = [w for w in words if h_top < w["top"] < h_bot
                  and w["text"] not in BOIL and not re.match(r"^[\d,%.]+$", w["text"])]
            stacks = []
            for w in sorted(hw, key=lambda a: ((a["x0"] + a["x1"]) / 2, a["top"])):
                c = (w["x0"] + w["x1"]) / 2
                for s in stacks:
                    if abs(s["c"] - c) < 25:
                        s["ws"].append(w)
                        s["c"] = sum((x["x0"] + x["x1"]) / 2 for x in s["ws"]) / len(s["ws"])
                        break
                else:
                    stacks.append({"c": c, "ws": [w]})
            nums = sorted((w for w in words if abs(w["top"] - trow["top"]) < 3
                           and re.match(r"^[\d,]+$", w["text"])), key=lambda w: w["x0"])
            bounds = [0.0]
            for vi in range(1, len(votes)):
                bounds.append((votes[vi - 1]["x0"] + votes[vi]["x0"]) / 2)
            bounds.append(pg.width)
            for vi, v in enumerate(votes):
                lo, hi = bounds[vi], bounds[vi + 1]
                t = min(titles, key=lambda t: abs(t["x0"] - v["x0"]))
                if not (lo <= t["x0"] + 5 and t["x0"] - 5 <= hi):
                    continue  # this VOTE anchor belongs to a non-alder contest
                cst = sorted((s for s in stacks if lo <= s["c"] < hi), key=lambda s: s["c"])
                names = [" ".join(x["text"] for x in sorted(s["ws"], key=lambda a: a["top"]))
                         for s in cst]
                cnm = [w for w in nums if lo <= (w["x0"] + w["x1"]) / 2 < hi]
                k = len(names)
                if not k or len(cnm) < k:
                    continue
                pairs = [(names[i], int(cnm[i]["text"].replace(",", ""))) for i in range(k)]
                winner = max(pairs, key=lambda p: p[1])
                if t["n"] in wins:
                    raise SystemExit("kenosha canvass: contest %d parsed twice" % t["n"])
                wins[t["n"]] = winner
    return wins


def scrape_kenosha():
    d = json.loads(fetch(KENOSHA_GIS))
    members = {}
    for f in d["features"]:
        a = f["attributes"]
        name = (a.get("REPRESNTTV") or "").strip()
        if name and name != "N/A":
            key = "%02d" % int(a["DIST_NO"])
            if key in members and members[key]["name"] != name:
                raise SystemExit("kenosha GIS names two people for district %s" % key)
            members[key] = {"name": name}
    if len(members) != 17:
        raise SystemExit("kenosha GIS names %d of 17 districts" % len(members))

    os.makedirs(CACHE_DIR, exist_ok=True)
    pdf_path = os.path.join(CACHE_DIR, "kenosha_canvass_2026_spring.pdf")
    if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) < 100000:
        open(pdf_path, "wb").write(fetch(KENOSHA_CANVASS, binary=True))
    wins = kenosha_canvass_winners(pdf_path)
    if len(wins) != 17:
        raise SystemExit("kenosha canvass parsed %d of 17 alderperson contests" % len(wins))
    bad = []
    for n in range(1, 18):
        key = "%02d" % n
        # subset, not equality: the ballot prints middle names the GIS omits
        # ("Brandi Rose Ferree" / "Ruth Delace Dyson", measured) — the same
        # person styled apart, where a different person shares no tokens
        a, b = fold_set(members[key]["name"]), fold_set(wins[n][0])
        agrees = bool(a and b and (a <= b or b <= a))
        # A PIN IS CONSULTED BEFORE THE AGREEMENT TEST, not after it. Reading
        # them the other way round is what let District 14's override outlive
        # its purpose in silence: once the GIS caught up, the agreement test
        # `continue`d and the "remove the pin" guard below became unreachable.
        if n in KENOSHA_CANVASS_WINS:
            pin = KENOSHA_CANVASS_WINS[n]
            if fold_set(wins[n][0]) != fold_set(pin["name"]):
                raise SystemExit("kenosha D%d: the pinned canvass override no longer "
                                 "matches the canvass (%r vs pin %r)" % (n, wins[n][0], pin["name"]))
            if agrees:
                raise SystemExit("kenosha D%d: the GIS now names the certified winner "
                                 "(%r) — the override has served its purpose; remove "
                                 "its KENOSHA_CANVASS_WINS entry"
                                 % (n, members[key]["name"]))
            stale = members[key]["name"]
            members[key] = {"name": pin["name"],
                            "note": "Elected April 2026 (certified by the Kenosha County "
                                    "Board of Canvassers)"}
            print("kenosha D%d: certified April 2026 winner %r ships over the GIS's "
                  "stale %r — %s" % (n, pin["name"], stale, pin["why"]),
                  file=sys.stderr)
            continue
        if agrees:
            continue
        bad.append((n, members[key]["name"], wins[n][0]))
    if bad:
        raise SystemExit("kenosha: GIS name(s) differ from the certified April 2026 "
                         "winner(s): %s — an appointment or a stale layer; needs a "
                         "human look (pin a KENOSHA_CANVASS_WINS entry only after "
                         "reading the story)" % bad)
    return members, KENOSHA_GIS.split("/query")[0]


# ------------------------------------------------------------------- Racine
def scrape_racine():
    page = fetch(RACINE_INDEX)
    members = {}
    # each staff card: a "District #N – Alderman NAME" heading, then a "Read
    # More and Contact" link to the district's own page (slugs inconsistent
    # across districts — captured, never composed)
    for m in re.finditer(r'District\s*#(\d+)\s*[–-]\s*'
                         r'Alder(?:man|woman|person)?\s+([^<]+?)\s*<', page):
        n, name = int(m.group(1)), " ".join(m.group(2).split())
        key = "%02d" % n
        if key in members and members[key]["name"] != name:
            raise SystemExit("racine lists two names for district %d" % n)
        entry = {"name": name}
        tail = page[m.end():m.end() + 800]
        u = re.search(r'href="(https://cityofracinewi\.gov[^"]*cityalderman/[^"]+)"', tail)
        if u:
            entry["url"] = u.group(1)
        members[key] = entry
    if len(members) != 15:
        raise SystemExit("racine names %d of 15 districts" % len(members))
    return members, RACINE_INDEX


# ----------------------------------------------------------------- Waukesha
def scrape_waukesha():
    lines = strip_tags(fetch(WAUKESHA_INDEX))
    members = {}
    i = 0
    while i < len(lines):
        m = re.match(r"^Aldermanic District (\d+)$", lines[i])
        # the page prints the district list twice; only the second pass has a
        # "Wards …" line under each heading, which is the block this reads
        if m and i + 2 < len(lines) and lines[i + 1].startswith("Wards"):
            n = int(m.group(1))
            entry = {"name": lines[i + 2]}
            j = i + 3
            while j < len(lines) and not lines[j].startswith("Aldermanic District"):
                if lines[j] == "P:" and j + 1 < len(lines):
                    entry["phone"] = lines[j + 1]
                if lines[j] == "E:" and j + 1 < len(lines) and "@" in lines[j + 1]:
                    entry["email"] = lines[j + 1]
                j += 1
            if not re.match(r"^[A-Z][A-Za-z.'\- ]+$", entry["name"]):
                raise SystemExit("waukesha district %d name line reads %r — the "
                                 "block shape moved" % (n, entry["name"]))
            members["%02d" % n] = entry
            i = j
        else:
            i += 1
    if len(members) != 15:
        raise SystemExit("waukesha names %d of 15 districts" % len(members))
    return members, WAUKESHA_INDEX


# ======================================================== the twelve of 2026-09-05
# One helper first. TWO OF THEM PRINT A WARD NUMBER WHERE THE KEY IS A
# DISTRICT: Menomonie's council page reads "Jeff Luther, Ward 1" and Viroqua's
# table reads "WARD 1 | SETH MCCLURG", while the file this roster keys into is
# dissolved on ALDERID. In both cities every ward is its own district today and
# ward N carries ALDERID N — measured 2026-09-05, 11 of 11 and 9 of 9 — but that
# is a fact about a filing, not about the English language, and a re-warding
# would silently move every name one seat. So it is WITNESSED on every run from
# the same publisher whose file draws the districts: if the identity breaks,
# those two cities fail (isolated, carried forward) rather than shipping a
# plausible wrong answer.
_LTSB_CACHE = {}


def ltsb_ward_to_alder(mcd_name, ctv):
    """{ward int -> ALDERID str} for one municipality, from LTSB's ward layer."""
    key = (mcd_name, ctv)
    if key not in _LTSB_CACHE:
        q = urllib.parse.urlencode({
            "where": "MCD_NAME='%s' AND CTV='%s'" % (mcd_name.replace("'", "''"), ctv),
            "outFields": "WARDID,ALDERID", "returnGeometry": "false",
            "f": "json", "resultRecordCount": 500})
        d = json.loads(fetch(LTSB_WARDS + "?" + q))
        if "error" in d:
            raise SystemExit("LTSB ward query failed for %s: %s"
                             % (mcd_name, d["error"]))
        rows = [f["attributes"] for f in d.get("features", [])]
        if not rows:
            raise SystemExit("LTSB carries no %s %s wards" % (mcd_name, ctv))
        _LTSB_CACHE[key] = {int(r["WARDID"]): (r["ALDERID"] or "").strip()
                            for r in rows}
    return _LTSB_CACHE[key]


def require_ward_is_district(mcd_name, ctv, seats):
    """The city numbers its seats by ward; assert ward N IS district N."""
    m = ltsb_ward_to_alder(mcd_name, ctv)
    if len(m) != seats:
        raise SystemExit("%s: the state files %d wards for a %d-seat council, so "
                         "its page's ward numbers can no longer be read as "
                         "districts" % (mcd_name, len(m), seats))
    bad = sorted("%d->%s" % (w, a) for w, a in m.items() if a != "%02d" % w)
    if bad:
        raise SystemExit("%s: ward and district have stopped coinciding (%s) — the "
                         "council page numbers seats by ward and cannot be keyed "
                         "to districts any more" % (mcd_name, ", ".join(bad)))


# ------------------------------------------------------------- Stevens Point
def scrape_stevens_point():
    """The city's CivicPlus staff directory, one category per body.

    Its districts are ORDINAL WORDS ("First District"), each printed TWICE per
    entry — the responsive layout renders one copy for wide and one for narrow,
    exactly Green Bay's shape — so the split is on the entry container.
    NO E-MAIL SHIPS AND THAT IS THE CITY'S CHOICE: every "Email Ald. X" link
    is a /formcenter/ form, not a mailto, so there is no address to carry.
    """
    page = fetch(STEVENS_POINT_DIR)
    members = {}
    for li in re.split(r'<li class="list-group-item', page)[1:]:
        t = re.search(r">\s*(%s)\s+District\s*<" % "|".join(ORDINALS), li, re.I)
        if not t:
            continue
        n = ORDINALS[t.group(1).lower()]
        nm = re.search(r'href="(/m/directory/employee\?eid=\d+)"[^>]*>\s*([^<]+?)\s*<', li)
        if not nm:
            continue
        entry = {"name": " ".join(nm.group(2).split()),
                 "url": "https://stevenspoint.com" + nm.group(1)}
        ph = re.search(r'href="tel:([^",]+)', li)
        if ph:
            entry["phone"] = ph.group(1).strip()
        key = "%02d" % n
        if key in members and members[key]["name"] != entry["name"]:
            raise SystemExit("stevens point lists two names for district %d" % n)
        members[key] = entry
    if len(members) != 11:
        raise SystemExit("stevens point names %d of 11 districts" % len(members))
    return members, STEVENS_POINT_DIR


# ----------------------------------------------------------------- Menomonie
def scrape_menomonie():
    """"NAME, Ward N" per <li>, in two columns. The mayor's row says ", Mayor"
    and carries no ward, which is what keeps him out."""
    require_ward_is_district("Menomonie", "C", 11)
    page = fetch(MENOMONIE_INDEX)
    members = {}
    for li in re.findall(r"<li\b[^>]*>(.*?)</li>", page, re.S):
        m = re.search(r"</a>\s*,\s*Ward\s+(\d{1,2})\b", li)
        if not m:
            continue
        nm = re.search(r'href="(/[Dd]irectory\.aspx\?EID=\d+)"[^>]*>([^<]+)</a>', li)
        if not nm:
            raise SystemExit("menomonie: a ward row with no directory link (%r)"
                             % li[:120])
        n = int(m.group(1))
        entry = {"name": " ".join(nm.group(2).split()),
                 "url": "https://www.menomonie-wi.gov" + nm.group(1)}
        key = "%02d" % n
        if key in members and members[key]["name"] != entry["name"]:
            raise SystemExit("menomonie lists two names for ward %d" % n)
        members[key] = entry
    if len(members) != 11:
        raise SystemExit("menomonie names %d of 11 wards" % len(members))
    return members, MENOMONIE_INDEX


# ----------------------------------------------------------------- Manitowoc
def scrape_manitowoc():
    """The Common Council table: NAME | District | Term | Phone.

    TWO TRAPS, BOTH IN THE NAME COLUMN. Two anchors carry a title= attribute
    naming the PREVIOUS alderperson — title="Scott McMeans" on the row whose
    text reads "Chad Beeman", title="Steve Czekala" on Brett Norell's — so a
    title-keyed read ships two people who left. The anchor TEXT is the name.
    And one row's href points at wi-manitowoc2.civicplus.com, the site's own
    staging host; only on-domain links ship, so that district carries no url
    rather than a link to a staging copy.

    The mayor's table sits above and has three columns and no district, so
    requiring a district cell is what excludes him.
    """
    page = fetch(MANITOWOC_INDEX)
    members = {}
    for row in re.findall(r"<tr\b[^>]*>(.*?)</tr>", page, re.S):
        cells = re.findall(r"<td\b[^>]*>(.*?)</td>", row, re.S)
        if len(cells) != 4:
            continue
        nm = re.search(r"<a\b[^>]*>\s*([^<]+?)\s*</a>", cells[0])
        dm = re.match(r"^\s*(\d{1,2})\s*(?:<br\s*/?>)?\s*$", cells[1])
        if not (nm and dm):
            continue
        n = int(dm.group(1))
        name = " ".join(H.unescape(nm.group(1)).split())
        entry = {"name": name}
        href = re.search(r'href="([^"]+)"', cells[0])
        # `/path` or an absolute manitowoc.org URL, and NEVER `//host/path`,
        # which urljoin would turn into somebody else's origin
        if href and re.match(r"^(?:https?://(?:www\.)?manitowoc\.org)?/(?!/)",
                             href.group(1)):
            entry["url"] = urllib.parse.urljoin(MANITOWOC_INDEX, href.group(1))
        ph = re.search(r"\(?\d{3}\)?[\s.-]\s*\d{3}-\d{4}", cells[3])
        if ph:
            entry["phone"] = " ".join(ph.group(0).split())
        key = "%02d" % n
        if key in members and members[key]["name"] != name:
            raise SystemExit("manitowoc lists two names for district %d" % n)
        members[key] = entry
    if len(members) != 10:
        raise SystemExit("manitowoc names %d of 10 districts" % len(members))
    return members, MANITOWOC_INDEX


# ----------------------------------------------- Sheboygan and Eau Claire
def civicplus_hcards(page):
    """[(name, job title, profile href)] for a CivicPlus staff-directory
    widget. Two cities below publish their council through it, one h-card per
    member, and the job title is where the district lives."""
    out = []
    for li in re.split(r'<li class="widgetItem h-card"', page)[1:]:
        nm = re.search(r'class="widgetTitle field p-name">\s*(.*?)\s*</h4>', li, re.S)
        jt = re.search(r'class="field p-job-title">\s*(.*?)\s*</div>', li, re.S)
        if not (nm and jt):
            continue
        u = re.search(r'class="field p-link"><a href="([^"]+)"', li)
        out.append((" ".join(re.sub(r"<[^>]+>", " ", H.unescape(nm.group(1))).split()),
                    " ".join(re.sub(r"<[^>]+>", " ", H.unescape(jt.group(1))).split()),
                    u.group(1) if u else None))
    return out


def scrape_sheboygan():
    """One h-card per member, the job title reading "District N (Wards a, b)"
    with a council role sometimes appended.

    THE PAGE'S WARD LISTS ARE BEHIND THE STATE'S FILE — District 9 names wards
    17 and 18 where LTSB also files ward 23 there — so the ward parenthesis is
    read as prose and never as a key; the district number is the key.

    ROBOTS: sheboyganwi.gov's `*` group is `Allow: /` with
    Content-Signal: search=yes,ai-train=no,use=reference. Nine crawlers are
    disallowed BY NAME (Amazonbot, CCBot, ClaudeBot, GPTBot and the rest); this
    weekly civic-data fetch is none of them, nothing here trains on the page,
    and naming the alderperson with a link back to this page is the reference
    use the signal permits. Recorded so the reading is visible and the operator
    can drop this city if they read it differently.

    THE OPERATOR READ IT AND KEPT IT, 2026-09-05. This paragraph was written as
    an open question for exactly that decision; it has been answered, and the
    reading above stands as the reason rather than as a proposal.
    """
    members = {}
    for name, title, href in civicplus_hcards(fetch(SHEBOYGAN_INDEX)):
        d = re.search(r"District\s+(\d{1,2})\b", title)
        if not d:
            continue
        n = int(d.group(1))
        entry = {"name": name}
        if href:
            entry["url"] = urllib.parse.urljoin(SHEBOYGAN_INDEX, href)
        key = "%02d" % n
        if key in members and members[key]["name"] != name:
            raise SystemExit("sheboygan lists two names for district %d" % n)
        members[key] = entry
    if len(members) != 10:
        raise SystemExit("sheboygan names %d of 10 districts" % len(members))
    return members, SHEBOYGAN_INDEX


def scrape_eau_claire():
    """The same widget, job titles reading "City Council - District N".

    THIS CITY WAS RECORDED AS BLOCKED AND IS NOT. The gap record has said since
    2026-08-26 that "Eau Claire and Janesville sit behind Akamai denies";
    measured 2026-09-05, https://www.eauclairewi.gov/310/City-Council answers
    200 with all five district councillors on it. Whatever the earlier probe
    met, the claim was carried forward without being re-measured — and a
    blocked-by-default record is how a readable source stays unread.

    Eau Claire seats ELEVEN and only FIVE are districted: the council is five
    district members, five at-large and a president, whose h-cards carry a job
    title with no district in it and are excluded by requiring one. The other
    six are a City-card fact, not an aldermanic-district one.
    """
    members = {}
    for name, title, href in civicplus_hcards(fetch(EAU_CLAIRE_INDEX)):
        d = re.search(r"City Council\s*[-–]\s*District\s+(\d{1,2})\b", title)
        if not d:
            continue
        n = int(d.group(1))
        entry = {"name": name}
        if href:
            entry["url"] = urllib.parse.urljoin(EAU_CLAIRE_INDEX, href)
        key = "%02d" % n
        if key in members and members[key]["name"] != name:
            raise SystemExit("eau claire lists two names for district %d" % n)
        members[key] = entry
    if len(members) != 5:
        raise SystemExit("eau claire names %d of 5 districts" % len(members))
    return members, EAU_CLAIRE_INDEX


# ------------------------------------------------------------------ Superior
def scrape_superior():
    """One table row per councilor: a left cell headed "Nth District - Area",
    a right cell with the name in an h1.headline, a mailto and a phone.

    TWO REASONS THIS PARSES PER ROW AND NEVER OVER THE PAGE: every bio repeats
    its own ordinal in prose ("1st District Councilor Nicholas Ledin is…"), and
    the district-5 heading is misspelt "5th Disrtict", which is why the anchor
    is the ordinal plus "Dis" rather than the whole word.

    There is also a VILLAGE of Superior (COUSUBFP 78660, one uncoded ward). The
    city is 78650 and is the only one of the two with districts.
    """
    page = fetch(SUPERIOR_INDEX)
    members = {}
    for row in re.findall(r"<tr\b[^>]*>(.*?)</tr>", page, re.S):
        d = re.search(r"(\d{1,2})(?:st|nd|rd|th)\s+Dis[a-z]*\b", row, re.I)
        nm = re.search(r'<h1 class="headline">\s*(.*?)\s*</h1>', row, re.S)
        if not (d and nm):
            continue
        n = int(d.group(1))
        name = " ".join(re.sub(r"<[^>]+>", " ", H.unescape(nm.group(1))).split())
        entry = {"name": name}
        em = re.search(r'href="mailto:([^"?]+)"', row)
        if em:
            entry["email"] = em.group(1).strip()
        ph = re.search(r"\(\d{3}\)\s*\d{3}-\d{4}", re.sub(r"<[^>]+>", " ", row))
        if ph:
            entry["phone"] = " ".join(ph.group(0).split())
        key = "%02d" % n
        if key in members and members[key]["name"] != name:
            raise SystemExit("superior lists two names for district %d" % n)
        members[key] = entry
    if len(members) != 10:
        raise SystemExit("superior names %d of 10 districts" % len(members))
    return members, SUPERIOR_INDEX


# ------------------------------------------------------------------- Portage
def scrape_portage():
    """Contact cards: <strong>NAME</strong>, then "District N Alderperson
    Term …", then a line this parser must never read, then a phone, then a
    mailto.

    THE THIRD LINE IS THE ALDERPERSON'S HOME ADDRESS. Portage publishes it; the
    fleet does not ship one for anybody, so the card is read field by field —
    the name from the <strong>, the district from the line that says District,
    the phone by its own shape and the address from the mailto — and the line
    between the district and the phone is never touched.
    """
    page = fetch(PORTAGE_INDEX)
    members = {}
    for card in re.split(r'<div class="card-body">', page)[1:]:
        card = card.split("</div>")[0]
        nm = re.search(r"<strong>\s*([^<]+?)\s*</strong>", card)
        d = re.search(r"District\s+(\d{1,2})\s+Alderperson", card)
        if not (nm and d):
            continue
        n = int(d.group(1))
        name = " ".join(H.unescape(nm.group(1)).split())
        entry = {"name": name}
        em = re.search(r'href="mailto:([^"?]+)"', card)
        if em:
            entry["email"] = em.group(1).strip()
        ph = re.search(r"(?<![-\d])\d{3}-\d{3}-\d{4}(?![-\d])",
                       re.sub(r"<[^>]+>", " ", card))
        if ph:
            entry["phone"] = ph.group(0)
        key = "%02d" % n
        if key in members and members[key]["name"] != name:
            raise SystemExit("portage lists two names for district %d" % n)
        members[key] = entry
    if len(members) != 9:
        raise SystemExit(
            "portage names %d of 9 districts [%s]"
            % (len(members),
               body_note(page, ("card-body", r'<div class="card-body">'),
                         ("<strong>", r"<strong>"),
                         ("District N Alderperson",
                          r"District\s+\d{1,2}\s+Alderperson"))))
    return members, PORTAGE_INDEX


# ============================= the tranche of 2026-09-05 evening (five cities)
# All five pair every district with a name, and NONE was parsed by a shared
# routine: a generic "nearest name to District N" pass was written first and
# would have shipped "City Council President" as Eagle River's district 3 and
# "Edit Form" as Altoona's district 6. Per-city functions, as the fleet does.
#
# FIVE of the ten cities worked are DELIBERATELY NOT HERE:
#   * ALGOMA, DODGEVILLE, OCONOMOWOC and HORICON each seat TWO alderpersons
#     per district on staggered terms (Dodgeville's district 1 is Shaun Sersch
#     2025-2027 AND Roxanne Reynolds-Lair 2026-2028; Horicon's is Forrest
#     Frami AND Lisa Sullivan). The roster schema is members[district] -> one
#     member, so shipping any of them would name one of each pair and conceal
#     the other. Shut on the SCHEMA, not on the source. All four WERE built
#     and then withdrawn once _put() refused the second name.
#   * WAUPACA's page numbers its districts 1-5 while LTSB keys its geometry
#     41-45. That correspondence is plausible and NOT witnessed by anything
#     read here, and a wrong offset moves every name one seat, so it is not
#     guessed. (The builder's stray-district gate would catch it, which is why
#     the failure would be loud rather than silent — but a gate catching a
#     guess is not the same as not guessing.)


def _clean(fragment):
    """Tag-stripped, entity-decoded, whitespace-collapsed text."""
    return " ".join(re.sub(r"<[^>]+>", " ", H.unescape(fragment)).split())


def _contact(fragment):
    """{email, phone} from one member's own markup fragment — never a page's."""
    out = {}
    em = re.search(r'href="mailto:([^"?]+)"', fragment)
    if em:
        out["email"] = em.group(1).strip()
    ph = re.search(r"\(?\d{3}\)?[ .-]\d{3}-\d{4}", _clean(fragment))
    if ph:
        out["phone"] = ph.group(0).strip()
    return out


def _put(city, members, key, entry):
    """Record one member, and REFUSE a second name for the same district.

    THIS IS THE GUARD THAT MATTERS HERE, and it exists because its absence
    shipped a plausible half-truth: a `setdefault` took the first name and
    dropped the second in silence, so Dodgeville read as four alderpersons
    when the page names eight. The schema is members[district] -> ONE member,
    so a city that seats two per district cannot be represented at all, and
    naming one of each pair would conceal the other rather than merely be
    incomplete. Fail loudly instead.
    """
    if key in members and members[key]["name"] != entry["name"]:
        raise SystemExit("%s names two people for district %s (%s and %s) — the "
                         "roster schema holds one member per district, so this "
                         "city cannot ship without concealing a seat"
                         % (city, key, members[key]["name"], entry["name"]))
    members[key] = entry


def body_note(page, *markers):
    """"body N B; <marker> xM; ..." — what the fetch actually contained.

    A COUNT GATE THAT ONLY SAYS "0 of 9" CANNOT BE DIAGNOSED. Portage failed
    that way three times in five on 2026-09-05 and the log gave no way to tell
    a page that had changed shape from a body that was not the page at all; a
    day later it parsed 12 times out of 12 and the cause is still unknown. So
    every count failure now reports what came back, and the next occurrence is
    readable from the CI log alone instead of needing a live re-fetch that may
    no longer reproduce it.
    """
    bits = ["body %d B" % len(page)]
    for label, pat in markers:
        bits.append("%s x%d" % (label, len(re.findall(pat, page))))
    return "; ".join(bits)


def _seats_or_die(city, members, seats, page=None, *markers):
    if len(members) != seats:
        note = (" [%s]" % body_note(page, *markers)) if page is not None else ""
        raise SystemExit("%s names %d of %d districts%s"
                         % (city, len(members), seats, note))
    return members


# ---------------------------------------------------------------- New Lisbon
def scrape_new_lisbon():
    """"Ward <list> Council Member | <name> | Phone: | ... | Term Expires:".

    THE CITY NUMBERS ITS SEATS BY WARD GROUP, not by district: "Ward 1, 6 and
    7 Council Member", "Ward 2 Council Member", "Ward 3", "Ward 4 and 5". That
    grouping IS the district plan and LTSB says so independently — its ward
    layer maps 1, 6 and 7 to ALDERID 01, 2 to 02, 3 to 03, and 4 and 5 to 04 —
    so the pairing is witnessed live on every run rather than assumed, the same
    posture Menomonie and Viroqua take for their one-ward-per-district pages.
    A re-warding that broke the grouping fails here instead of moving a name.

    E-MAIL IS NOT READ: the page serves every address through Cloudflare's
    obfuscation ("[email protected]"), which is an access control and is not
    worked around. The phones are published in the clear and do ship.
    """
    ward_to_alder = ltsb_ward_to_alder("New Lisbon", "C")
    page = fetch(NEW_LISBON_INDEX)
    flat = re.sub(r"\|+", "|", re.sub(r"<[^>]+>", "|", H.unescape(page)))
    members = {}
    for m in re.finditer(r"Ward\s+([\d,\s and]+?)\s+Council Member[\s|]+"
                         r"([A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]*\.?){1,3})"
                         r"((?:[^|]*\|){0,4})", flat):
        wards = [int(w) for w in re.findall(r"\d+", m.group(1))]
        ids = {ward_to_alder.get(w) for w in wards}
        if len(ids) != 1 or None in ids:
            raise SystemExit(
                "new lisbon: the page groups wards %s as one seat and LTSB puts "
                "them in districts %s — the ward plan moved, so which seat this "
                "name holds is not settled" % (wards, sorted(x for x in ids if x)))
        entry = {"name": m.group(2).strip()}
        ph = re.search(r"\(?\d{3}\)?[ .-]?\d{3}-\d{4}", m.group(3))
        if ph:
            entry["phone"] = " ".join(ph.group(0).split())
        _put("new lisbon", members, ids.pop(), entry)
    return _seats_or_die("new lisbon", members, 4, page,
                         ("Ward .. Council Member",
                          r"Ward\s+[\d,\s and]+?\s+Council Member")), NEW_LISBON_INDEX


# ---------------------------------------------------------------- New Berlin
def scrape_new_berlin():
    """Cards whose NAME PRECEDES the "District N" label."""
    page = fetch(NEW_BERLIN_INDEX)
    flat = re.sub(r"<[^>]+>", "|", H.unescape(page))
    flat = re.sub(r"\|+", "|", flat)
    members = {}
    for m in re.finditer(r"([A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]*\.?){1,3})"
                         r"[\s|]+District\s+(\d{1,2})\b", flat):
        _put("new berlin", members, "%02d" % int(m.group(2)), {"name": m.group(1).strip()})
    return _seats_or_die("new berlin", members, 7, page,
                         ("District N", r"District\s+\d{1,2}\b")), NEW_BERLIN_INDEX


# -------------------------------------------------------------- Sturgeon Bay
def scrape_sturgeon_bay():
    """"District N | <name> | <home address> | <phone> | sbdistrictN@...".

    The page also carries an AT-LARGE mayor, who has no district and so is
    never matched. THE CELL AFTER THE NAME IS A HOME ADDRESS and is stepped
    over by shape — the phone and the per-seat district mailbox after it are
    the city's own official contact for the seat and do ship.
    """
    page = fetch(STURGEON_BAY_INDEX)
    flat = re.sub(r"\|+", "|", re.sub(r"<[^>]+>", "|", H.unescape(page)))
    members = {}
    for m in re.finditer(r"District\s+(\d{1,2})\b[\s|]+"
                         r"([A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]*\.?){1,3})"
                         r"([^|]*(?:\|[^|]*){0,3})", flat):
        entry = {"name": m.group(2).strip()}
        tail = m.group(3)
        ph = re.search(r"\(?\d{3}\)?[ .-]\d{3}-\d{4}", tail)
        if ph:
            entry["phone"] = ph.group(0).strip()
        em = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", tail)
        if em:
            entry["email"] = em.group(0).strip()
        _put("sturgeon bay", members, "%02d" % int(m.group(1)), entry)
    return _seats_or_die("sturgeon bay", members, 7, page,
                         ("District N", r"District\s+\d{1,2}\b")), STURGEON_BAY_INDEX


# ------------------------------------------------------------------- Altoona
def scrape_altoona():
    """"<Name> | Council Person District N (Ward a, b) | Term expires | phone".

    The name PRECEDES the label. A name-follows read gets "Edit Form" for
    district 6 — the page's trailing contact widget, which sits exactly where
    the seventh member would be if there were one.
    """
    page = fetch(ALTOONA_INDEX)
    flat = re.sub(r"\|+", "|", re.sub(r"<[^>]+>", "|", H.unescape(page)))
    members = {}
    for m in re.finditer(r"([A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]*\.?){1,3})"
                         r"[\s|]+Council Person\s+District\s+(\d{1,2})\b", flat):
        _put("altoona", members, "%02d" % int(m.group(2)), {"name": m.group(1).strip()})
    return _seats_or_die("altoona", members, 6, page,
                         ("Council Person District N",
                          r"Council Person\s+District\s+\d{1,2}\b")), ALTOONA_INDEX


# --------------------------------------------------------------- Eagle River
def scrape_eagle_river():
    """"Aldermanic District N, Wards a & b" then an OPTIONAL office title and
    then the name.

    DISTRICT 3'S TITLE IS THE TRAP: its block reads "... District 3, Wards 3 &
    4 | City Council President | Kim Schaffer", so the first capitalised run
    after the label is an office, not a person. Titles are skipped by name.
    """
    page = fetch(EAGLE_RIVER_INDEX)
    flat = re.sub(r"\|+", "|", re.sub(r"<[^>]+>", "|", H.unescape(page)))
    titles = ("City Council President", "Council President", "Mayor",
              "City Council Vice President")
    members = {}
    for m in re.finditer(r"Aldermanic\s+District\s+(\d{1,2})\b[^|]*((?:\|[^|]*){1,16})",
                         flat):
        cells = [c.strip() for c in m.group(2).split("|") if c.strip()]
        cells = [c for c in cells if c not in titles]
        if not cells:
            raise SystemExit("eagle river: district %s has only a title"
                             % m.group(1))
        entry = {"name": cells[0]}
        tail = m.group(2)
        ph = re.search(r"\(?\d{3}\)?[ .-]?\d{3}-\d{4}", tail)
        if ph:
            entry["phone"] = " ".join(ph.group(0).split())
        em = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", tail)
        if em:
            entry["email"] = em.group(0).strip()
        _put("eagle river", members, "%02d" % int(m.group(1)), entry)
    return _seats_or_die("eagle river", members, 4, page,
                         ("Aldermanic District N",
                          r"Aldermanic\s+District\s+\d{1,2}\b")), EAGLE_RIVER_INDEX


# ---------------------------------------------------------------- Germantown
def scrape_germantown():
    """A VILLAGE: its four are TRUSTEES, and the card renders them as such.
    "District N" then the trustee's name."""
    page = fetch(GERMANTOWN_INDEX)
    flat = re.sub(r"\|+", "|", re.sub(r"<[^>]+>", "|", H.unescape(page)))
    members = {}
    for m in re.finditer(r"District\s+(\d{1,2})\b[\s|]+"
                         r"([A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]*\.?){1,3})", flat):
        _put("germantown", members, "%02d" % int(m.group(1)), {"name": m.group(2).strip()})
    return _seats_or_die("germantown", members, 4, page,
                         ("District N", r"District\s+\d{1,2}\b")), GERMANTOWN_INDEX


# ------------------------------------------------------------------- Viroqua
def scrape_viroqua():
    """A five-column table: WARD N | NAME | Term Expires | mailto | tel.

    The city numbers its seats by ward, so the same LTSB witness Menomonie uses
    applies here; the MAYOR row's first cell says MAYOR and carries no number,
    which is what excludes it. Names print in capitals and ship that way — this
    project renders what the publisher wrote.
    """
    require_ward_is_district("Viroqua", "C", 9)
    page = fetch(VIROQUA_INDEX)
    members = {}
    for row in re.findall(r"<tr\b[^>]*>(.*?)</tr>", page, re.S):
        cells = re.findall(r"<td\b[^>]*>(.*?)</td>", row, re.S)
        if len(cells) < 2:
            continue
        w = re.match(r"^\s*WARD\s+(\d{1,2})\s*$",
                     re.sub(r"<[^>]+>", " ", H.unescape(cells[0])).strip(), re.I)
        if not w:
            continue
        n = int(w.group(1))
        name = " ".join(re.sub(r"<[^>]+>", " ", H.unescape(cells[1])).split())
        if not name:
            raise SystemExit("viroqua: ward %d has no name cell" % n)
        entry = {"name": name}
        em = re.search(r'href="mailto:([^"?]+)"', row)
        if em:
            entry["email"] = em.group(1).strip()
        ph = re.search(r"\(\d{3}\)\s*\d{3}-\d{4}", re.sub(r"<[^>]+>", " ", row))
        if ph:
            entry["phone"] = " ".join(ph.group(0).split())
        key = "%02d" % n
        if key in members and members[key]["name"] != name:
            raise SystemExit("viroqua lists two names for ward %d" % n)
        members[key] = entry
    if len(members) != 9:
        raise SystemExit("viroqua names %d of 9 wards" % len(members))
    return members, VIROQUA_INDEX


# ------------------------------------------------------------------- Menasha
def scrape_menasha():
    """Eight table cells, laid out DOWN THE COLUMNS (1, 5, 2, 6, 3, 7, 4, 8),
    each headed "District N Alderperson" with the name under it.

    TWO THINGS ARE DELIBERATELY NOT READ. The line under each name is the
    alderperson's HOME ADDRESS, which never ships. And District 1's cell
    contains href="mailto:rnichols@ci.menasha.wi.us" wrapping an empty <br> —
    that is not Chris Rand's address, and taking it would attach one person's
    mail to another's name, the same shape as the county page whose footer
    webmaster@ once shipped as a sheriff. So NO e-mail ships for Menasha; the
    city routes contact through a per-district "Contact Me" form anyway.
    """
    page = fetch(MENASHA_INDEX)
    members = {}
    for cell in re.findall(r"<td\b[^>]*>(.*?)</td>", page, re.S):
        d = re.search(r"District\s+(\d{1,2})\s+Alderperson", cell)
        if not d:
            continue
        n = int(d.group(1))
        after = cell[d.end():]
        nm = re.search(r"<strong>\s*(?:<[^>]+>\s*)*([^<]+?)\s*<", after)
        if not nm:
            raise SystemExit("menasha: district %d cell has no name in bold" % n)
        name = " ".join(H.unescape(nm.group(1)).split())
        if not re.match(r"^[A-ZÀ-Þ][A-Za-zÀ-ÿ.'’ -]+$", name):
            raise SystemExit("menasha district %d name reads %r — the cell shape "
                             "moved" % (n, name))
        entry = {"name": name}
        ph = re.search(r"\(\d{3}\)\s*\d{3}-\d{4}", re.sub(r"<[^>]+>", " ", after))
        if ph:
            entry["phone"] = " ".join(ph.group(0).split())
        key = "%02d" % n
        if key in members and members[key]["name"] != name:
            raise SystemExit("menasha lists two names for district %d" % n)
        members[key] = entry
    if len(members) != 8:
        raise SystemExit("menasha names %d of 8 districts" % len(members))
    return members, MENASHA_INDEX


# -------------------------------------------------------------------- Howard
def scrape_howard():
    """A village, not a city: eight TRUSTEE districts, one <li> each, reading
    "NAME, District N (Wards a-b)". The Village President sits in his own list
    above with ", Village President" and no district, which is what keeps a
    citywide officer off a district card."""
    page = fetch(HOWARD_INDEX)
    members = {}
    for li in re.findall(r"<li\b[^>]*>(.*?)</li>", page, re.S):
        d = re.search(r"District\s+(\d{1,2})\b", re.sub(r"<[^>]+>", " ", li))
        nm = re.search(r'href="([^"]*[Dd]irectory\.aspx\?EID=\d+)"[^>]*>(.*?)</a>',
                       li, re.S)
        if not (d and nm):
            continue
        n = int(d.group(1))
        name = " ".join(re.sub(r"<[^>]+>", " ", H.unescape(nm.group(2))).split())
        # THE PAGE MIXES SCHEMES: six of the eight anchors are https and two —
        # districts 1 and 7 — are written http, which urljoin preserves because
        # they are absolute. The host serves both and redirects, but a card that
        # hands a reader an http link on a site that has https is shipping the
        # worse of two addresses the publisher itself uses. Upgraded on this
        # host only, and only for a bare http scheme.
        href = re.sub(r"^http://(www\.villageofhoward\.com)", r"https://\1",
                      nm.group(1))
        entry = {"name": name,
                 "url": urllib.parse.urljoin(HOWARD_INDEX, href)}
        key = "%02d" % n
        if key in members and members[key]["name"] != name:
            raise SystemExit("howard lists two names for district %d" % n)
        members[key] = entry
    if len(members) != 8:
        raise SystemExit("howard names %d of 8 trustee districts" % len(members))
    return members, HOWARD_INDEX


# --------------------------------------------------------------------- Tomah
def scrape_tomah():
    """Drupal view rows: the title field is the member's name and profile link,
    the position field reads "District N Alderperson". The mayor's row has the
    same shape with position "Mayor", so requiring a district excludes him."""
    page = fetch(TOMAH_INDEX)
    members = {}
    for row in re.split(r'<div class="views-row', page)[1:]:
        nm = re.search(r'views-field-title[^>]*>.*?<a href="([^"]+)"[^>]*>\s*'
                       r'([^<]+?)\s*</a>', row, re.S)
        pos = re.search(r'views-field-field-position.*?class="field-content">\s*'
                        r'([^<]*?)\s*</div>', row, re.S)
        if not (nm and pos):
            continue
        d = re.search(r"District\s+(\d{1,2})\b", H.unescape(pos.group(1)))
        if not d:
            continue
        n = int(d.group(1))
        name = " ".join(H.unescape(nm.group(2)).split())
        entry = {"name": name,
                 "url": urllib.parse.urljoin(TOMAH_INDEX, nm.group(1))}
        key = "%02d" % n
        if key in members and members[key]["name"] != name:
            raise SystemExit("tomah lists two names for district %d" % n)
        members[key] = entry
    if len(members) != 8:
        raise SystemExit("tomah names %d of 8 districts" % len(members))
    return members, TOMAH_INDEX




# ------------------------------------------------------------------ Appleton
def scrape_appleton():
    """The city's common-council page, one directory block per alderperson:
    "<h2>NAME, District N</h2>", a "Read More" link to that district's own
    city page, and a tel: link.

    SHIPPED FROM 2026-09-05, when the geometry it rides finally could be drawn
    — Outagamie County still files every Appleton ward uncoded, and the city
    clerk's own polling-locations page supplies the composition instead
    (build_wi_aldermanic_districts.py, LOCAL_COMPOSITION). This roster route
    had been verified readable and recorded as WAITING for that geometry since
    2026-08-26; a roster with no card to ride is not shipped.

    TWO TRAPS. Five members link a personal blog, Wordpress site or Facebook
    page from the same block; those are the member's own, not the city's, so
    the url read here is the `rz-bus-readmore` anchor — the city's district
    page — and its district number is cross-checked against the heading's.
    AND THE PAGE CARRIES `<base href="https://www.appletonwi.gov/">`, so its
    relative hrefs resolve against the SITE ROOT rather than against the page's
    own directory: joining `government/district_1.php` to the page URL gives
    /government/government/district_1.php, which answers 404 (measured). The
    base is read from the page and its absence fails the city, because the day
    it disappears is the day every link here would silently become a 404.
    """
    page = fetch(APPLETON_INDEX)
    base = re.search(r'<base\b[^>]*href="([^"]+)"', page, re.I)
    if not base:
        raise SystemExit("appleton: the page no longer declares a <base href>, so its "
                         "relative links cannot be resolved the way a browser does")
    base_url = urllib.parse.urljoin(APPLETON_INDEX, base.group(1))
    members = {}
    for block in re.split(r"<h2>", page)[1:]:
        h = re.match(r"\s*([^<,]+?)\s*,\s*District\s+(\d{1,2})\s*</h2>", block)
        if not h:
            continue
        name, n = " ".join(H.unescape(h.group(1)).split()), int(h.group(2))
        entry = {"name": name}
        u = re.search(r'href="(government/district_(\d{1,2})\.php)"[^>]*'
                      r'class="rz-bus-readmore"', block)
        if u:
            if int(u.group(2)) != n:
                raise SystemExit("appleton: %s is headed District %d and its Read More "
                                 "goes to district_%s.php" % (name, n, u.group(2)))
            entry["url"] = urllib.parse.urljoin(base_url, u.group(1))
        ph = re.search(r'href="tel:([^"]+)"', block)
        if ph:
            digits = re.sub(r"\D", "", ph.group(1))
            if len(digits) == 10:
                entry["phone"] = "(%s) %s-%s" % (digits[:3], digits[3:6], digits[6:])
        key = "%02d" % n
        if key in members and members[key]["name"] != name:
            raise SystemExit("appleton lists two names for district %d" % n)
        members[key] = entry
    if len(members) != 15:
        raise SystemExit("appleton names %d of 15 districts" % len(members))
    return members, APPLETON_INDEX


# ONE UNREACHABLE SERVER NEVER TAKES THE OTHERS DOWN — AND A BROKEN READING
# TAKES EVERYTHING DOWN ON PURPOSE. The distinction is the whole design and it
# was stated wrongly in this repo until 2026-09-05: the workflow's comment and
# this module's docstring both said a municipality whose page reshapes "fails
# its own gate" in isolation, which is false.
#
# WHAT IS ISOLATED. Until 2026-09-03 the six scrapes ran unguarded and any raise
# ended the run, so greenbaywi.gov timing out after three 60-second tries cost
# Milwaukee, Madison, Kenosha, Racine and Waukesha their weekly refresh as well
# — 82 alderpersons dropped because one city's webserver was slow. `attempt()`
# catches `Exception`, so that class of failure — a timeout, a reset, an HTTP
# error, a malformed body — is now caught per municipality, and
# `build_wi_alderperson_roster.py` carries that municipality's last shipped rows
# forward, names it in the log, and refuses if too many are carried at once. The
# reason travels in `failures` so the weekly PR's reviewer sees WHICH server was
# unreadable rather than inferring it from an absence.
#
# WHAT IS NOT, AND MUST NOT BE. Every gate in this file raises `SystemExit`, and
# `SystemExit` inherits from `BaseException` rather than `Exception` — so a gate
# failure walks straight past `attempt()` and ends the run. THAT IS THE SAFE
# DIRECTION AND THE CATCH IS DELIBERATELY NOT WIDENED. A timeout means "not
# today"; a gate failure means a pinned reading has stopped being true, and the
# honest response to that is to stop, not to carry a municipality forward under
# a date that says the run went fine. Widening this to `BaseException` would
# turn every reshaped page into a silent six-week-old roster.
def attempt(label, fn):
    """(result, None) on success; (None, reason) on an UNREACHABLE source.

    Never catches a gate failure — see the block above. `SystemExit` is not an
    `Exception`, and that is the point rather than an oversight.
    """
    try:
        return fn(), None
    except Exception as e:                   # noqa: BLE001 - reported per city
        reason = "%s: %s" % (type(e).__name__, str(e)[:150])
        print("  MISS %-12s %s" % (label, reason), file=sys.stderr)
        return None, reason


def main():
    argv = sys.argv[1:]
    out_path = argv[argv.index("--out") + 1] if "--out" in argv else DEFAULT_OUT

    got, failures = {}, {}
    for code, name, seats, fn in (
            ("53000", "Milwaukee", 15, scrape_milwaukee),
            ("48000", "Madison", 20, scrape_madison),
            ("31000", "Green Bay", 12, scrape_green_bay),
            ("39225", "Kenosha", 17, scrape_kenosha),
            ("66000", "Racine", 15, scrape_racine),
            ("84250", "Waukesha", 15, scrape_waukesha),
            ("77200", "Stevens Point", 11, scrape_stevens_point),
            ("51025", "Menomonie", 11, scrape_menomonie),
            ("48500", "Manitowoc", 10, scrape_manitowoc),
            ("72975", "Sheboygan", 10, scrape_sheboygan),
            ("78650", "Superior", 10, scrape_superior),
            ("64100", "Portage", 9, scrape_portage),
            ("82925", "Viroqua", 9, scrape_viroqua),
            ("50825", "Menasha", 8, scrape_menasha),
            ("35950", "Howard", 8, scrape_howard),
            ("80075", "Tomah", 8, scrape_tomah),
            ("22300", "Eau Claire", 5, scrape_eau_claire),
            ("02375", "Appleton", 15, scrape_appleton),
            # the tranche of 2026-09-05 evening
            ("56375", "New Berlin", 7, scrape_new_berlin),
            ("77875", "Sturgeon Bay", 7, scrape_sturgeon_bay),
            ("01550", "Altoona", 6, scrape_altoona),
            ("21625", "Eagle River", 4, scrape_eagle_river),
            ("28875", "Germantown", 4, scrape_germantown),
            ("56900", "New Lisbon", 4, scrape_new_lisbon)):
        result, reason = attempt(name, fn)
        if result is None:
            failures[code] = {"municipality": name, "reason": reason}
            continue
        # Madison alone returns a third value: the districts it says are vacant
        members, source = result[0], result[1]
        entry = {"municipality": name, "seats": seats, "sourceUrl": source,
                 "members": members}
        if len(result) > 2:
            entry["vacantDistricts"] = result[2]
        got[code] = entry

    if not got:
        raise SystemExit("every city failed (%s) — that is a network or a code "
                         "fault, not six simultaneous site changes"
                         % "; ".join(f["reason"] for f in failures.values()))

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump({"cities": got, "failures": failures}, f, indent=2,
                  ensure_ascii=False)
    total = sum(len(c["members"]) for c in got.values())
    madison = got.get("48000", {}).get("vacantDistricts")
    print("scraped %d alderpersons across %d of %d municipalities (Madison "
          "vacant: %s)%s -> %s"
          % (total, len(got), len(CITIES), madison or "none",
             "" if not failures else "; MISSED %s" % ", ".join(
                 sorted(f["municipality"] for f in failures.values())),
             out_path))


if __name__ == "__main__":
    main()
