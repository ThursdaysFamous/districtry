#!/usr/bin/env python3
"""
Build the clerk, deputy clerk, phone, website and per-record currency date for
EVERY ONE of Wisconsin's 1,847 municipalities, from the Elections Commission's
own statewide directory. TWO OUTPUTS, because the app has two cards:

  data/app/wi-municipal-clerks.json   608 cities and villages, keyed by
                                      7-digit Census PLACE GEOID, read by the
                                      City or Village card.
  data/app/town-clerks-<CCC>.json     1,239 towns, keyed by 10-digit COUNTY
                                      SUBDIVISION GEOID, one file per county,
                                      read by the County Subdivision card.

ONE SCRIPT AND NOT TWO, because the expensive half is shared: the 395-page
parse, the label traps, the name casing and the two address labels this build
refuses all apply identically to a town. Splitting them would give two copies
of `field_of` to keep in step, and one `--check` covers both halves.

THE TWO HALVES KEY DIFFERENTLY AND THAT IS THE WHOLE REASON THEY ARE SEPARATE
FILES. A city or village is a Census PLACE; a town is a Census COUNTY
SUBDIVISION; the two numbering systems are unrelated, and each card can only
look up the key its own layer hands it. Cities and villages also appear in the
subdivision fabric (671 records for 608 municipalities, since 58 cross a county
line), but they are NOT written to the town files: the County Subdivision card
already tells a city or village reader that their municipality "also answers on
the City or Village card", so the clerk belongs on that one and repeating it
here would put the same row on two cards at one point.

WHY THIS EXISTS. The City or Village card has named an officeholder in exactly
nineteen municipalities since 2026-09-03 — Milwaukee County's mayors and
village presidents, the only source in the state that publishes municipal
EXECUTIVES as data (build_wi_municipal_executives.py). The other 589 cities
and villages got their name, their FIPS code and nothing else. This closes
that to 608 of 608 with a different officer: not the executive, but the CLERK,
who is the one municipal officer Wisconsin aggregates statewide.

A CLERK IS NOT A MAYOR AND THE CARD MUST NOT IMPLY OTHERWISE. The clerk runs
the municipality's elections and keeps its records; the executive leads it.
Both rows can appear on one card and they are labelled separately. This build
does not close the `municipal-officers` gap, which is about the governing
BODY — it narrows it, and the gap record says so.

THE SOURCE, AND WHY IT IS A COMMITTED FILE. `WI Municipal Clerks Updated
8-4-2026.pdf`, sent by the Commission's Jodi Vitcenda on 2026-08-27 (help-desk
ticket 123582) and ALSO published at https://elections.wi.gov/clerks/directory
— a URL this project cannot fetch. The Commission's front page clears a real
browser; every interior /clerks/* path re-challenges the same cleared session,
measured over 17 interior attempts in two CI runs. So the committed copy is
the build input and the published URL is what a future re-pull uses.
`wi/data/source/wec/README.md` carries the whole arrangement.

THE PARSE IS POSITIONAL, NOT TEXT-FLOW, and the report's own ruling lines are
what make it safe. Microsoft Reporting Services draws one horizontal rule
between records, so a record is the band between two rules and its five fields
are five x-ranges within that band. Flattening the page instead (pypdf) reads
in a plausible order that silently interleaves a long municipality name with
the next record's clerk.

FOUR MEASURED TRAPS, ALL ENCODED:

  1. A HYPHENATED SURNAME WRAPS MID-WORD and its continuation line looks
     exactly like an address continuation. Two records do it — Ashland's
     "CHIANNE SCHWEITZER-" + "MONAHAN" and Cudahy's "MELISSA VENANCIO-" +
     "LEONARD" — and a line-based read ships both truncated. The rule is
     exact: a CLERK/DEPUTY CLERK line must be FOLLOWED by another label, and
     where it is not, the next line continues the name. Gated twice: the
     continuation is joined, and no shipped name may end in a hyphen.
  2. FOUR MUNICIPALITY NAMES ARE MIXED CASE in a file that is otherwise all
     caps ("Village of SALEM LAKES", "Village of Rib Mountain", "Village of
     Raymond", "Village of Yorkville"), so a case-sensitive header match
     drops them.
  3. THREE NAMES DIFFER FROM THE CENSUS BY WORDS, not punctuation, and they
     are THE SAME THREE build_wi_polling_places.py already measured against
     LTSB — Mt. Sterling / Mount Sterling, LaValle / La Valle, Fontana /
     Fontana-on-Geneva Lake. That the same three miss against a THIRD
     publisher makes the table a fact about WEC's vocabulary rather than
     about LTSB's, which is why it is restated here against Census basenames
     instead of imported: the counterparts are different strings.
  4. THE COUNTY COLUMN IS SOMETIMES "MULTIPLE COUNTIES" — 58 municipalities,
     the identical 58 the polling file labels that way, two Commission files
     agreeing. The join here is by name and kind and never by county, so this
     costs nothing; it is asserted because a change in that count means the
     Commission re-shaped the file.

THE JOIN IS TO THE CARD'S OWN FABRIC. The municipality layer is a live read of
TIGERweb's Places layer 4, so this build asks that same layer for Wisconsin
and keys the output by the GEOID the card will hold. Anything else — LTSB's
municipality key, WEC's own five-digit code — would be a key the card cannot
look up. Measured 2026-09-03: 608 TIGER places, 609 WEC city/village records,
605 matching directly, 3 through the aliases above, and ONE WEC village with
no Census counterpart at all.

THAT ONE IS ALREADY THIS INSTANCE'S RECORDED GAP. The Village of French Island
(La Crosse County) incorporated out of the Town of Campbell; TIGERweb still
carries neither name in its Places layer, which is gap `french-island-census-
lag` with its own WATCH.md row. It is dropped here because the card has no
polygon to draw for it — there is no City or Village card at that point to put
a clerk row on — and every run PRINTS the unmatched list, so the day the
Census catches up this build says so and the gap can be retired.

WHAT DELIBERATELY DOES NOT SHIP, both measured rather than assumed:

  * NO E-MAIL. There is none to ship: 0 of 1,848 records contain "@", the
    PDF's own /Subject metadata reads "WI Municipal Clerks PDF - no emails:",
    and the Commission said why — "that was at their request". It is a
    withholding by the people named, so nothing here goes looking for those
    addresses elsewhere to backfill them.
  * NO ADDRESS, AND THE ADDRESS LABELS ARE NEVER EVEN READ. Every record
    carries Municipal Address and Mailing Address, and the file has no field
    telling a village hall from the clerk's own house. Clerks serving several
    municipalities prove it without guessing at any one address: Lori Opitz
    files ONE street address under the Town of Oconomowoc and the VILLAGE OF
    LAC LA BELLE, Tom Monacelli one under the Town of Warren and the VILLAGE
    OF LOHRVILLE, Amber Larson one across four towns. Two of those reach a
    village, which is this card. Extracting the field and dropping it later
    would leave a leak one edit away; `field_of` refuses the label instead.

THE TOWN JOIN NEEDS THE COUNTY AND THE CITY JOIN DOES NOT, which is measured
rather than a matter of taste: Wisconsin has a Town of Unity in Clark AND a
Town of Unity in Trempealeau, and they are different towns with different
clerks. A name-only join would put one's clerk on the other's card. The county
comes from the app's own `state-counties.json`, and TIGER's 1,242 town records
give 1,242 distinct (county, name) keys, so the pair is a key and the name
alone is not. No town crosses a county line — 0 of 1,239 are filed under
MULTIPLE COUNTIES, against 58 cities and villages — so a town is exactly one
subdivision record.

Usage:
    python3 wi/scripts/build_wi_municipal_clerks.py
    python3 wi/scripts/build_wi_municipal_clerks.py --check    # operator gate
    python3 wi/scripts/build_wi_municipal_clerks.py --pdf /path/to/newer.pdf

NOT A CI GATE, for the same reason build_wi_polling_places.py is not: --check
rebuilds, and rebuilding needs TIGERweb. What guards this file in CI is
validate_index.py's roster floor on its key count. Re-run --check by hand
after replacing the PDF.
"""

import argparse
import collections
import datetime
import json
import os
import re
import sys
import urllib.parse
import urllib.request
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                                "scripts"))
from scraper_common import require_robots_once, UA_STDLIB_DEFAULT  # noqa: E402  (FLEET_SHARED)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INSTANCE_ROOT = os.path.dirname(SCRIPT_DIR)
APP_DATA_DIR = os.path.join(INSTANCE_ROOT, "data", "app")
DEFAULT_PDF = os.path.join(INSTANCE_ROOT, "data", "source", "wec",
                           "WI Municipal Clerks Updated 8-4-2026.pdf")
OUT_PATH = os.path.join(APP_DATA_DIR, "wi-municipal-clerks.json")

SOURCE_NAME = "Wisconsin Elections Commission"
SOURCE_URL = "https://elections.wi.gov/clerks/directory"
SOURCE_FILE = "WI Municipal Clerks Updated 8-4-2026.pdf"

# The card's own layer: TIGERweb Places, layer 4 — the same service and layer
# wi/index.html's `loadPlaces` reads, so the key here is the key it holds.
TIGER_PLACES = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                "Places_CouSub_ConCity_SubMCD/MapServer/4/query")
LSADC_KIND = {"25": "CITY", "47": "VILLAGE"}

EXPECT_RECORDS = 1848        # the file's own municipality count, 8/4/2026
EXPECT_PLACES = 608          # TIGER's WI cities + villages; the join must be total
EXPECT_MULTI_COUNTY = 58     # trap 4; the polling file's identical figure
MIN_PHONES = 570             # measured 608 — a floor against the column emptying
MIN_WEBSITES = 490           # measured 545, likewise (the Barron rule: a floor
                             # is a measurement of what a source publishes,
                             # never a target for it)

# The TOWN half. TIGER's county-subdivision layer is the fabric the County
# Subdivision card reads, and it carries 1,242 town records against the
# directory's 1,239 towns.
COUSUB_LAYER = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                "Places_CouSub_ConCity_SubMCD/MapServer/1/query")
EXPECT_COUSUB = 1925         # the whole subdivision fabric, the card's own figure
EXPECT_TOWN_RECORDS = 1242   # of which towns
EXPECT_WEC_TOWNS = 1239      # the directory's towns
MIN_TOWN_PHONES = 1150       # measured 1,238 of 1,239 (the Town of Marion,
                             # Waushara, is the one with none)
MIN_TOWN_WEBSITES = 750      # measured 830

# SEVENTY-ONE COUNTY FILES, NOT SEVENTY-TWO. Milwaukee County contains no
# towns at all — every one of its 19 municipalities is a city or a village,
# which is also why it is the one county whose executives the county itself
# publishes (build_wi_municipal_executives.py). A 72nd file means Wisconsin
# created a town; a 70th means one was absorbed. Either is a human's business.
EXPECT_TOWN_COUNTIES = 71

# NO TOWN CROSSES A COUNTY LINE, and that is measured rather than assumed from
# the statute: 0 of the directory's 1,239 towns is filed under MULTIPLE
# COUNTIES (58 cities and villages are), and TIGER's 1,242 town records give
# 1,242 DISTINCT (county, name) keys. Both halves matter — Wisconsin has a Town
# of Unity in Clark AND in Trempealeau, and a name-only join would put one
# town's clerk on the other's card, which is the trap
# build_wi_polling_places.py records for the same pair of publishers.
EXPECT_TOWN_MULTI_COUNTY = 0

# THE THREE TOWNS TIGER CARRIES AND THE DIRECTORY DOES NOT, each named so a
# FOURTH fails this build instead of quietly shipping a card with no clerk.
# All three are the same phenomenon — a town/village boundary the two
# publishers draw differently — and none is a parse defect:
#
#   Harrison town (Calumet)     the Village of Harrison incorporated out of it
#                               and WEC files only the village (MULTIPLE
#                               COUNTIES: Calumet + Outagamie). What is left is
#                               24,739 m2 — six acres — and the Commission's
#                               polling file has no reporting unit for it
#                               either, which is one of the 30 unpaired wards.
#   Bloomfield town (Walworth)  the same shape: WEC files the Village of
#                               Bloomfield in Walworth and no town. (The Town
#                               of Bloomfield in WAUSHARA is a different town
#                               and does match.)
#   Campbell town (La Crosse)   this is the Village of French Island under the
#                               Census's own older name — gap
#                               `french-island-census-lag`. Its clerk is NOT
#                               attached here: doing so would assert an
#                               identity the Census does not, which is exactly
#                               what that gap record refuses to do.
#
# All three are FUNCSTAT 'A', so the Census considers them current; this is a
# disagreement between publishers, not a stale row.
TOWNS_WITHOUT_A_CLERK = {
    ("015", "HARRISON"): "the Village of Harrison incorporated out of it; WEC files only the village",
    ("127", "BLOOMFIELD"): "the Village of Bloomfield incorporated out of it; WEC files only the village",
    ("063", "CAMPBELL"): "the Census's own older name for the Village of French Island (gap french-island-census-lag)",
}

# Trap 3 again, on the town half. Both are the SAME municipalities the polling
# builder's own table names, and St. Lawrence is character-for-character its
# entry — a fourth publisher, the same two names.
TOWN_ALIASES = {
    ("125", "LAND O LAKES"): ("125", "LAND OLAKES"),   # WEC "LAND O- LAKES"; the
                                                       # hyphen strips to a SPACE,
                                                       # which `norm` keeps
    ("135", "SAINT LAWRENCE"): ("135", "ST LAWRENCE"),
}

# Trap 3. WEC's spelling -> the Census BASENAME, both normalized. Deliberately
# not imported from build_wi_polling_places.MUNI_ALIASES: that table maps the
# same three WEC names onto LTSB's strings, which are different again
# ("FONTANAONGENEVA LAKE" here is the Census's "Fontana-on-Geneva Lake").
MUNI_ALIASES = {
    ("VILLAGE", "MT STERLING"): ("VILLAGE", "MOUNT STERLING"),
    ("VILLAGE", "LAVALLE"): ("VILLAGE", "LA VALLE"),
    ("VILLAGE", "FONTANA"): ("VILLAGE", "FONTANAONGENEVA LAKE"),
}

# Every label the clerk column uses, measured across all 1,848 records. The two
# ADDRESS labels are here so `field_of` can REFUSE them by name — see the
# module docstring: a field that is never extracted cannot leak.
CELL_LABELS = ("CLERK", "DEPUTY CLERK", "MUNICIPAL ADDRESS", "MAILING ADDRESS",
               "PHONE 1", "PHONE 2", "FAX")
NEVER_READ = ("MUNICIPAL ADDRESS", "MAILING ADDRESS")

LABEL_RE = re.compile(r"(?i)^(CLERK|DEPUTY CLERK|Municipal Address|Mailing "
                      r"Address|Phone \d|Fax)\s*:")
KIND_RE = re.compile(r"^(TOWN|VILLAGE|CITY) OF\b", re.I)   # trap 2: IGNORECASE
COLUMNS = (("muni", 0, 145), ("code", 145, 192), ("cell", 192, 381),
           ("web", 381, 525), ("updated", 525, 620))

# Suffixes and prefixes plain .capitalize() gets wrong on a PERSON's name. The
# shared scripts/vtd_board_districts.title_case is for census BASENAMEs and its
# own docstring says a name with an apostrophe "needs an explicit label rather
# than this function" — O'MALLEY and O'NEILL are two of these 608, so it is the
# wrong tool here rather than one to bend.
_SUFFIX = {"JR", "SR", "II", "III", "IV", "V"}


def fail(msg):
    print("build-wi-municipal-clerks: FAIL — %s" % msg, file=sys.stderr)
    sys.exit(1)


def person_case(name):
    """"MELISSA VENANCIO-LEONARD" -> "Melissa Venancio-Leonard".

    Handles the four shapes measured in these 608 that .capitalize() gets
    wrong: hyphenated surnames (14), Mc/Mac prefixes (13), apostrophes (2) and
    a generational suffix (1). Every one of those is capitalized on BOTH sides
    of its separator, which is what .capitalize() will not do.
    """
    def cap(word):
        if not word:
            return word
        if word.upper().strip(".") in _SUFFIX:
            return word.upper().strip(".")
        # McCANN -> McCann, MacDONALD -> MacDonald; the inner capital is real
        for pre in ("MC", "MAC"):
            if len(word) > len(pre) + 1 and word.upper().startswith(pre):
                return pre.capitalize() + word[len(pre):].capitalize()
        return word.capitalize()

    def cap_parts(chunk, seps="-'"):
        for sep in seps:
            if sep in chunk:
                return sep.join(cap_parts(p, seps) for p in chunk.split(sep))
        return cap(chunk)

    return " ".join(cap_parts(w) for w in str(name).split())


def norm(s):
    """Uppercase, delete . ' and -, collapse whitespace. The same three rules
    build_wi_polling_places.norm applies, because the left-hand side of both
    joins is the same publisher's vocabulary."""
    s = str(s).upper()
    for ch in (".", "'", "-"):
        s = s.replace(ch, "")
    return re.sub(r"\s+", " ", s).strip()


def cell_text(words, x0, x1):
    """The lines of one column of one record band, in reading order."""
    sel = sorted((w for w in words if x0 <= w["x0"] < x1),
                 key=lambda w: (round(w["top"], 1), w["x0"]))
    lines, line, last = [], [], None
    for w in sel:
        top = round(w["top"], 1)
        if last is not None and abs(top - last) > 2.5:
            lines.append(" ".join(line))
            line = []
        line.append(w["text"])
        last = top
    if line:
        lines.append(" ".join(line))
    return [l.strip() for l in lines if l.strip()]


def field_of(lines, label):
    """The value of one label in the clerk column, or None.

    Trap 1 lives here: a CLERK/DEPUTY CLERK line whose NEXT line is not itself
    a label has wrapped, and the next line is the rest of the name.
    """
    want = label.upper()
    if want in NEVER_READ:
        # Not defensive programming — the whole address decision. See the
        # module docstring and wi/data/source/wec/README.md.
        raise AssertionError("%s is never read by this build" % label)
    for i, ln in enumerate(lines):
        if not ln.upper().startswith(want + ":"):
            continue
        value = ln.split(":", 1)[1].strip()
        nxt = lines[i + 1] if i + 1 < len(lines) else None
        if nxt is not None and not LABEL_RE.match(nxt):
            value = (value + nxt).strip() if value.endswith("-") \
                else (value + " " + nxt).strip()
        return value or None
    return None


def split_muni(lines):
    """(kind, bare name, county) from the wrapped municipality column."""
    start = next((i for i, l in enumerate(lines) if KIND_RE.match(l)), None)
    if start is None:
        return None, None, None
    joined = re.sub(r"\s+", " ", " ".join(lines[start:])).strip()
    if " - " not in joined:
        return None, None, None
    name, county = joined.rsplit(" - ", 1)
    kind = KIND_RE.match(name).group(1).upper()
    bare = re.sub(r"(?i)^(TOWN|VILLAGE|CITY) OF\s+", "", name).strip()
    return kind, bare, county.strip()


def iso_date(us):
    """"12/18/2023" -> "2023-12-18". The Commission's per-record currency."""
    try:
        m, d, y = [int(p) for p in str(us).strip().split("/")]
        return datetime.date(y, m, d).isoformat()
    except (ValueError, TypeError):
        return None


def read_pdf(path):
    import pdfplumber                      # heavy; function-local by convention
    records = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            rules = sorted({round(l["top"], 1) for l in page.lines})
            words = page.extract_words()
            for top, bottom in zip(rules, rules[1:]):
                band = [w for w in words if top + 1 <= w["top"] < bottom - 1]
                if not band:
                    continue
                cols = {k: cell_text(band, a, b) for k, a, b in COLUMNS}
                code = "".join(cols["code"]).strip()
                if not code.isdigit():
                    continue               # the header band and the page footer
                records.append((code, cols))
    return records


def tiger_places():
    """Wisconsin's incorporated places, from the card's own service."""
    query = urllib.parse.urlencode({
        "where": "STATE='55'", "outFields": "GEOID,NAME,BASENAME,LSADC",
        "returnGeometry": "false", "f": "json", "resultRecordCount": "2000",
    })
    try:
        require_robots_once(TIGER_PLACES + "?" + query, UA_STDLIB_DEFAULT, label="wi-build-wi-municipal-clerks")
        with urllib.request.urlopen(TIGER_PLACES + "?" + query, timeout=120) as r:
            payload = json.load(r)
    except Exception as e:                  # noqa: BLE001 - reported, not raised
        fail("TIGERweb did not answer (%s). This build joins to the card's own "
             "place fabric, so it cannot run offline." % e)
    if payload.get("exceededTransferLimit"):
        fail("TIGERweb paged its answer; this build assumes one page of "
             "Wisconsin places and would silently ship a partial join")
    feats = payload.get("features") or []
    places = {}
    for f in feats:
        a = f["attributes"]
        kind = LSADC_KIND.get(str(a.get("LSADC")))
        if not kind:
            fail("TIGERweb returned LSADC %r, which is neither a city (25) nor "
                 "a village (47)" % a.get("LSADC"))
        key = (kind, norm(a["BASENAME"]))
        if key in places:
            fail("two Wisconsin places share the key %r — the name join this "
                 "build relies on is no longer unique" % (key,))
        places[key] = a
    return places


def town_path(fips):
    """data/app/town-clerks-<county FIPS>.json — the name the card builds out of
    the GEOID it already holds (`55` + county + subdivision), so there is no
    name-to-slug table here or in the app to drift."""
    return os.path.join(APP_DATA_DIR, "town-clerks-%s.json" % fips)


def county_fips_map():
    """County NAME -> 3-digit FIPS, from the app's OWN shipped county file.

    Not a compiled table and not another TIGERweb call: state-counties.json is
    what the county card draws, so a county this build cannot place is a county
    the app cannot draw either. The directory writes "ADAMS COUNTY" and that
    file's NAME is "Adams County", so `norm` matches them with no suffix
    stripping — an early draft stripped " COUNTY" from one side only and
    matched zero of 1,239.
    """
    path = os.path.join(APP_DATA_DIR, "state-counties.json")
    if not os.path.exists(path):
        fail("no %s — the town join keys on the app's own county fabric" % path)
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    feats = payload["features"] if isinstance(payload, dict) else payload
    out = {}
    for feat in feats:
        props = feat.get("properties") or {}
        geoid = str(props.get("GEOID") or props.get("geoid") or "")
        name = props.get("NAME") or props.get("name") or props.get("BASENAME")
        if geoid and name:
            out[norm(name)] = geoid[-3:]
    if len(out) != 72:
        fail("state-counties.json gave %d counties, expected Wisconsin's 72"
             % len(out))
    return out


def cousub_towns():
    """(county FIPS, normalized name) -> TIGER town record, for all 1,242."""
    query = urllib.parse.urlencode({
        "where": "STATE='55'", "outFields": "GEOID,NAME,BASENAME,COUNTY,LSADC",
        "returnGeometry": "false", "f": "json", "resultRecordCount": "4000",
    })
    try:
        require_robots_once(COUSUB_LAYER + "?" + query, UA_STDLIB_DEFAULT, label="wi-build-wi-municipal-clerks")
        with urllib.request.urlopen(COUSUB_LAYER + "?" + query, timeout=120) as r:
            payload = json.load(r)
    except Exception as e:                       # noqa: BLE001 - reported, not raised
        fail("TIGERweb's county-subdivision layer did not answer (%s)" % e)
    if payload.get("exceededTransferLimit"):
        fail("TIGERweb paged the subdivision fabric; this build assumes one page")
    feats = [f["attributes"] for f in (payload.get("features") or [])]
    if len(feats) != EXPECT_COUSUB:
        fail("TIGERweb returned %d Wisconsin county subdivisions, expected %d — "
             "the fabric the County Subdivision card draws has changed"
             % (len(feats), EXPECT_COUSUB))
    towns = {}
    for a in feats:
        name, base = a.get("NAME") or "", a.get("BASENAME") or ""
        # the card derives the type the same way, from NAME beyond BASENAME,
        # so the two can never disagree about what a town is
        if not (name.startswith(base) and
                name[len(base):].strip().lower() == "town"):
            continue
        key = (a["COUNTY"], norm(base))
        if key in towns:
            fail("two town records share the key %r — the county+name join this "
                 "build relies on is no longer unique" % (key,))
        towns[key] = a
    if len(towns) != EXPECT_TOWN_RECORDS:
        fail("the subdivision fabric holds %d towns, expected %d"
             % (len(towns), EXPECT_TOWN_RECORDS))
    return towns


def build_towns(parsed, counties):
    """{county FIPS: {cousub GEOID: entry}} for the County Subdivision card.

    PER COUNTY because the whole set is ~582 KB and this is a network-first
    roster fetched on a click; per county it is ~4 KB, and the card can build
    the filename out of the GEOID it already holds (`55` + county + subdivision)
    with no name-to-slug table to drift. Same reasoning as the polling files,
    which split for the same reason.
    """
    towns = cousub_towns()
    by_county, matched, multi = {}, set(), 0
    stats = {"phones": 0, "sites": 0, "deputies": 0, "clerks": 0}
    for code, kind, name, county, cols in parsed:
        if kind != "TOWN":
            continue
        if county == "MULTIPLE COUNTIES":
            multi += 1
            continue
        fips = counties.get(norm(county))
        if not fips:
            fail("the directory files a town under %r, which is not one of "
                 "Wisconsin's 72 counties" % county)
        key = (fips, norm(name))
        key = TOWN_ALIASES.get(key, key)
        town = towns.get(key)
        if town is None:
            fail("Town of %s (%s) has no county-subdivision record. Either the "
                 "Census has renamed it or it needs an alias beside the two in "
                 "TOWN_ALIASES." % (name.title(), county.title()))
        matched.add(key)
        lines = cols["cell"]
        entry = {"municipality": town["BASENAME"]}
        for field, label in (("clerk", "CLERK"), ("deputyClerk", "DEPUTY CLERK"),
                             ("phone", "Phone 1")):
            value = field_of(lines, label)
            if value:
                entry[field] = person_case(value) if field != "phone" else value
        web = "".join(cols["web"]).strip() or None
        if web:
            entry["url"] = web            # published, not authored — see above
        asof = iso_date("".join(cols["updated"]))
        if asof:
            entry["recordUpdated"] = asof
        stats["clerks"] += 1 if entry.get("clerk") else 0
        stats["deputies"] += 1 if entry.get("deputyClerk") else 0
        stats["phones"] += 1 if entry.get("phone") else 0
        stats["sites"] += 1 if entry.get("url") else 0
        by_county.setdefault(fips, {})[town["GEOID"]] = entry

    if multi != EXPECT_TOWN_MULTI_COUNTY:
        fail("%d towns are filed under MULTIPLE COUNTIES, expected %d — a town "
             "that crosses a county line breaks the one-record-per-town join"
             % (multi, EXPECT_TOWN_MULTI_COUNTY))
    shipped = sum(len(v) for v in by_county.values())
    if shipped != EXPECT_WEC_TOWNS:
        fail("%d towns shipped, expected %d" % (shipped, EXPECT_WEC_TOWNS))
    if len(by_county) != EXPECT_TOWN_COUNTIES:
        fail("%d counties have towns, expected %d — see EXPECT_TOWN_COUNTIES"
             % (len(by_county), EXPECT_TOWN_COUNTIES))

    # THE UNMATCHED SET IS NAMED, NOT COUNTED: a fourth town losing its clerk
    # is a publisher change worth a human, and a count-only check would absorb
    # it silently the moment one of these three gained one.
    left = {k for k in towns if k not in matched}
    expected = set(TOWNS_WITHOUT_A_CLERK)
    if left != expected:
        extra = sorted(left - expected)
        gone = sorted(expected - left)
        fail("the towns with no clerk record are no longer the three recorded "
             "ones.%s%s Read TOWNS_WITHOUT_A_CLERK before changing it."
             % ("" if not extra else " NEWLY without a clerk: %s." % (extra,),
                "" if not gone else " Now HAS one (retire its entry): %s." % (gone,)))
    if stats["phones"] < MIN_TOWN_PHONES:
        fail("only %d of %d towns carry a phone (floor %d)"
             % (stats["phones"], shipped, MIN_TOWN_PHONES))
    if stats["sites"] < MIN_TOWN_WEBSITES:
        fail("only %d of %d towns carry a website (floor %d)"
             % (stats["sites"], shipped, MIN_TOWN_WEBSITES))
    return by_county, stats


def build(pdf_path):
    records = read_pdf(pdf_path)
    if len(records) != EXPECT_RECORDS:
        fail("the directory parsed to %d municipalities, expected %d — the "
             "Commission re-shaped the report, or the ruling lines this parse "
             "keys on moved" % (len(records), EXPECT_RECORDS))
    codes = collections.Counter(c for c, _ in records)
    dupes = [c for c, n in codes.items() if n > 1]
    if dupes:
        fail("municipality codes repeat (%s) — a record was read twice"
             % ", ".join(sorted(dupes)[:5]))

    parsed, multi = [], 0
    for code, cols in records:
        kind, name, county = split_muni(cols["muni"])
        if not kind:
            fail("a record's municipality column did not parse: %r" % (cols["muni"],))
        if county == "MULTIPLE COUNTIES":
            multi += 1
        parsed.append((code, kind, name, county, cols))
    if multi != EXPECT_MULTI_COUNTY:
        fail("%d municipalities are filed under MULTIPLE COUNTIES, expected %d"
             % (multi, EXPECT_MULTI_COUNTY))

    counties = county_fips_map()
    places = tiger_places()
    if len(places) != EXPECT_PLACES:
        fail("TIGERweb returned %d Wisconsin cities and villages, expected %d. "
             "If the Census has caught up with a new incorporation this is the "
             "signal to retire the `french-island-census-lag` gap and move this "
             "number." % (len(places), EXPECT_PLACES))

    roster, unmatched, matched_keys = {}, [], set()
    for code, kind, name, county, cols in parsed:
        if kind not in ("CITY", "VILLAGE"):
            continue                        # towns are the County Subdivision card
        key = (kind, norm(name))
        key = MUNI_ALIASES.get(key, key)
        place = places.get(key)
        if place is None:
            unmatched.append("%s of %s (%s)" % (kind.title(), name, county))
            continue
        matched_keys.add(key)
        lines = cols["cell"]
        clerk = field_of(lines, "CLERK")
        deputy = field_of(lines, "DEPUTY CLERK")
        phone = field_of(lines, "Phone 1")
        web = "".join(cols["web"]).strip() or None
        entry = {
            "municipality": place["BASENAME"],
            "wecMunicipality": "%s OF %s" % (kind, name.upper()),
            "county": county.title(),
            "wecCode": code,
            "source": SOURCE_NAME,
            "sourceUrl": SOURCE_URL,
            "sourceFile": SOURCE_FILE,
        }
        if clerk:
            entry["clerk"] = person_case(clerk)
        if deputy:
            entry["deputyClerk"] = person_case(deputy)
        if phone:
            entry["phone"] = phone
        if web:
            # `url` and not `website`: validate_card_links.py's PUBLISHED_KEYS
            # is {"url", "profileUrl"}, and a municipality's own site is exactly
            # the "somebody else published this" class that caps at WARN. Named
            # anything else it would be read as a URL this repo chose and FAIL
            # the monthly gate on every CDN-fronted village that refuses a
            # datacentre client. Illinois's municipal roster uses the same key.
            entry["url"] = web
        asof = iso_date("".join(cols["updated"]))
        if asof:
            entry["recordUpdated"] = asof
        roster[place["GEOID"]] = entry

    missing = sorted(k for k in places if k not in matched_keys)
    if missing:
        fail("%d of TIGERweb's cities and villages have no clerk record (%s%s) "
             "— the join is no longer total and the card would name a clerk in "
             "some places and not others with nothing saying why"
             % (len(missing), ", ".join("%s %s" % m for m in missing[:5]),
                "" if len(missing) <= 5 else ", …"))

    # Trap 1's second gate: a truncated surname is invisible on a card.
    torn = sorted(g for g, e in roster.items()
                  for v in (e.get("clerk"), e.get("deputyClerk")) if v and v.endswith("-"))
    if torn:
        fail("a shipped name ends in a hyphen (%s) — a hyphenated surname wrapped "
             "and its continuation line was not joined" % ", ".join(torn[:5]))

    phones = sum(1 for e in roster.values() if e.get("phone"))
    sites = sum(1 for e in roster.values() if e.get("url"))
    if phones < MIN_PHONES:
        fail("only %d of %d records carry a phone (floor %d)"
             % (phones, len(roster), MIN_PHONES))
    if sites < MIN_WEBSITES:
        fail("only %d of %d records carry a website (floor %d)"
             % (sites, len(roster), MIN_WEBSITES))
    towns, town_stats = build_towns(parsed, counties)
    return roster, towns, {
        "records": len(records), "unmatched": unmatched,
        "phones": phones, "sites": sites,
        "deputies": sum(1 for e in roster.values() if e.get("deputyClerk")),
        "towns": town_stats,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="verify the shipped file, write nothing")
    ap.add_argument("--pdf", default=DEFAULT_PDF,
                    help="the Commission's directory (default: the committed one)")
    args = ap.parse_args()

    if not os.path.exists(args.pdf):
        fail("no directory at %s" % args.pdf)
    roster, towns, stats = build(args.pdf)

    # One source block per county file rather than per record: the three source
    # strings are constant and repeating them 1,239 times is most of the weight.
    # The polling files carry `_source` the same way, and validate_index.py's
    # floor counts it as one more top-level key.
    outputs = [(OUT_PATH, json.dumps(roster, indent=2, ensure_ascii=False,
                                     sort_keys=True) + "\n")]
    for fips in sorted(towns):
        payload = dict(towns[fips])
        payload["_source"] = {"publisher": SOURCE_NAME, "sourceUrl": SOURCE_URL,
                              "sourceFile": SOURCE_FILE}
        outputs.append((town_path(fips),
                        json.dumps(payload, indent=2, ensure_ascii=False,
                                   sort_keys=True) + "\n"))

    if args.check:
        for path, body in outputs:
            rel = os.path.relpath(path, os.getcwd())
            if not os.path.exists(path):
                fail("%s is missing" % rel)
            with open(path, encoding="utf-8") as f:
                if f.read() != body:
                    fail("%s differs from a rebuild of the Commission's "
                         "directory — re-run this script without --check" % rel)
        stale = [f for f in os.listdir(APP_DATA_DIR)
                 if f.startswith("town-clerks-") and
                 os.path.join(APP_DATA_DIR, f) not in {p for p, _ in outputs}]
        if stale:
            fail("%d town file(s) in data/app that this build does not produce "
                 "(%s) — a county left behind after a rename ships stale clerks"
                 % (len(stale), ", ".join(sorted(stale)[:4])))
    else:
        os.makedirs(APP_DATA_DIR, exist_ok=True)
        for path, body in outputs:
            with open(path, "w", encoding="utf-8") as f:
                f.write(body)

    dates = sorted(e["recordUpdated"] for e in roster.values() if e.get("recordUpdated"))
    print("build-wi-municipal-clerks: OK — %d municipalities in the directory, "
          "%d cities and villages joined to the card's place fabric (%d of %d), "
          "%s" % (stats["records"], len(roster), len(roster), EXPECT_PLACES,
                  "verified" if args.check else "written"))
    print("  clerk %d/%d · deputy %d · phone %d · website %d"
          % (sum(1 for e in roster.values() if e.get("clerk")), len(roster),
             stats["deputies"], stats["phones"], stats["sites"]))
    if dates:
        print("  the Commission's own per-record currency runs %s to %s — the "
              "card dates each row rather than the file" % (dates[0], dates[-1]))
    print("  WEC city/village records with no Census place: %d%s"
          % (len(stats["unmatched"]),
             (" (" + "; ".join(stats["unmatched"]) + ")") if stats["unmatched"] else ""))
    if not stats["unmatched"]:
        print("  NOTE: that list is empty. It has held exactly one entry — the "
              "Village of French Island — since this build was written; an "
              "empty list means TIGERweb has caught up and the "
              "`french-island-census-lag` gap can be retired.")
    t = stats["towns"]
    print("  towns: %d shipped across %d county file(s) — clerk %d, deputy %d, "
          "phone %d, website %d" % (sum(len(v) for v in towns.values()), len(towns),
                                    t["clerks"], t["deputies"], t["phones"], t["sites"]))
    print("  3 of TIGER's %d town records have no clerk, all recorded: %s"
          % (EXPECT_TOWN_RECORDS,
             "; ".join("%s (%s)" % (k[1].title(), v.split(";")[0])
                       for k, v in sorted(TOWNS_WITHOUT_A_CLERK.items()))))
    print("  NOT IN THIS FILE, BY MEASUREMENT: no e-mail (the clerks asked the "
          "Commission to withhold them) and no address (the file cannot tell a "
          "village hall from a clerk's house). See the module docstring.")


if __name__ == "__main__":
    main()
