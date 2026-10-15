#!/usr/bin/env python3
"""
Build ky/data/app/ky-county-districts.json: the districts each Kentucky county's
governing body is elected from, where this project can prove the lines.

WHO IS ELECTED BY DISTRICT. In 104 counties the fiscal court's magistrates are
elected from magisterial districts (KRS 67.045, KRS 25.010). Louisville Metro
elects 26 council members from districts (KRS 67C) and Lexington-Fayette 12
(KRS 67A). The 14 commissioner counties elect their commissioners by the whole
county (KRS 67.060), so their residence districts are not drawn here.

LOUISVILLE AND LEXINGTON PUBLISH THEIR MAPS. LOJIC (the Louisville/Jefferson
County Information Consortium) and the Lexington-Fayette Urban County
Government each keep a council-district layer with the member's name on every
district, and both are read as published. Those names are not shipped here:
they go to data/source/ky-county-districts.source.json, where
build_ky_county_officials.py reads them to give each council member a
district, because names belong in the roster the app fetches network-first and
these lines belong in a cache-first file.

NO STATE AGENCY PUBLISHES THE MAGISTERIAL DISTRICTS. So they are COMPOSED, from
three things the state does publish:

  1. The State Board of Elections' precinct map (3,193 precincts, kept with the
     Division of Geographic Information). KRS 67.045(7) and KRS 117.055(1)(f)
     forbid a precinct to cross a magisterial district line, so every district
     is a union of whole precincts.
  2. The State Board's certified 2026 primary recap sheets, which report each
     contest precinct by precinct. A precinct whose sheet carries "Magistrate
     District 3" is in District 3: that race was on its ballot.
  3. The 2022 general election recap sheets, read the same way. A county's
     2022 answers are used only where they agree with every precinct the 2026
     sheets also place (at least two of them), because a county that redrew
     its districts after 2022 would otherwise be drawn from its old map.
     Measured 2026-10-15, 523 of 528 precincts placed by both elections agree,
     and the five that do not are in two counties, Bourbon and Crittenden.

  Two further rules fill what the sheets leave. An uncontested primary race is
  not on the ballot, so a district whose 2026 race had one candidate has no
  precinct on the sheet. Where exactly ONE district of a county is missing and
  every unplaced precinct is listed on the 2026 sheet, those precincts are
  that district. And where a county publishes its own magisterial map
  (COUNTY_MAPS), it places a leftover precinct only if it agrees with every
  precinct the ballots already placed.

THE COUNTY MAPS WERE THE TEST. Thirteen county-published maps were compared
with the precinct-built districts on 2026-10-15. Where a map is current the two
agree to within a precinct (Henderson, Shelby, Hardin, Warren's planning
commission map, Grayson, Marion, Spencer, Trimble: intersection over union
0.98 to 1.00 per district). Where they disagree, the ballots were the newer
witness: Logan's map carries 2010 populations, and Oldham's and Muhlenberg's
put a precinct in a district its voters did not vote in at two elections.

A COUNTY IS DRAWN ONLY WHEN EVERY PRECINCT IS PLACED, with three exceptions
that are not anyone's ballot: the Army posts at Fort Knox (Hardin, Bullitt) and
Fort Campbell (Christian), which the State Board maps as precincts with no
magistrate race. Hardin's own map leaves Fort Knox out of every district, and
so does this file. Any precinct with two answers keeps its county off the map.
Every county left off, and why, is in the source record.

THE LINES ARE THE STATE BOARD'S PRECINCT LINES, dissolved, then simplified with
Douglas-Peucker in one mapshaper run (interval=20, a 25 m fidelity ceiling as
South Carolina's council map), so a line two districts share is one arc.

    python3 ky/scripts/build_ky_county_districts.py --cache DIR   # fetch, build, write
    python3 ky/scripts/build_ky_county_districts.py --check       # offline gate (CI)
    python3 ky/scripts/build_ky_county_districts.py --selftest    # parsers, offline

Building needs poppler-utils (pdftotext, pdftoppm), tesseract-ocr for the
scanned 2022 sheets, shapely, requests and npx. --cache keeps every fetched
sheet's text and the precinct map, so a rebuild reads nothing twice.
"""

import argparse
import collections
import datetime
import hashlib
import html
import json
import math
import os
import random
import re
import subprocess
import sys
import tempfile
import time
from urllib.parse import quote, unquote, urljoin

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
REPO = os.path.dirname(INSTANCE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "scripts"))

APP = os.path.join(INSTANCE, "data", "app")
OUT_FILE = os.path.join(APP, "ky-county-districts.json")
OFFICIALS = os.path.join(APP, "ky-county-officials.json")
COUNTIES_FILE = os.path.join(APP, "state-counties.json")
RESULTS_2022 = os.path.join(INSTANCE, "data", "source", "ky-fiscal-court-2022-results.json")
RECORD = os.path.join(INSTANCE, "data", "source", "ky-county-districts.source.json")

PRECINCTS = ("https://services3.arcgis.com/ghsX9CKghMvyYjBU/arcgis/rest/services/"
             "Ky_SBE_VTD_Boundaries_WM/FeatureServer/0")
PRIMARY_PAGE = "https://elect.ky.gov/results/2020-2029/Pages/2026Primary-Recap-Sheets.aspx"
GENERAL_PAGE = "https://elect.ky.gov/results/2020-2029/Pages/2022-General-Recap-Sheets.aspx"

# The two merged governments' own council maps, read as published.
COUNCILS = {
    "21111": {"county": "Jefferson", "body": "metro",
              "url": "https://gis.lojic.org/maps/rest/services/LojicSolutions/"
                     "OpenDataPolitical/MapServer/8",
              "district": "COUNDIST", "name": "COUN_NAME", "expect": 26,
              "publisher": "LOJIC (Louisville/Jefferson County Information Consortium)"},
    "21067": {"county": "Fayette", "body": "urban-county",
              "url": "https://services1.arcgis.com/Mg7DLdfYcSWIaDnu/arcgis/rest/services/"
                     "Council_District/FeatureServer/0",
              "district": "DISTRICT", "name": "REP", "expect": 12,
              "publisher": "Lexington-Fayette Urban County Government"},
}

# County-published magisterial maps used to place a precinct the ballots leave
# unplaced, and only where the map agrees with every precinct the ballots do
# place. Each was read 2026-10-15; the field is where its district number is.
COUNTY_MAPS = {
    "Grayson": ("https://services6.arcgis.com/ZEEfHlyOqtzNL4oA/arcgis/rest/services/"
                "Grayson_Mag_Dists/FeatureServer/0", "PROP_NAME"),
    "Hardin": ("https://services1.arcgis.com/fYwcHOBzInDTQxh0/arcgis/rest/services/"
               "2024Magisterial_Dist/FeatureServer/0", "District"),
    "Marion": ("https://services1.arcgis.com/Txq2JUfAytfzQqPz/arcgis/rest/services/"
               "Magistrial_Boundaries/FeatureServer/0", "dist_num"),
    "Spencer": ("https://services5.arcgis.com/SRuaqVyoD8TEQJga/arcgis/rest/services/"
                "SpencerMagisterialPrecinct2023/FeatureServer/0", "Magisteria"),
    "Trimble": ("https://services5.arcgis.com/SRuaqVyoD8TEQJga/arcgis/rest/services/"
                "TrimbleMagisPrecinct/FeatureServer/1", "Magisteria"),
    "Warren": ("https://webgis.bgky.org/server/rest/services/CCPC/"
               "CCPC_Magisterial_Voting_Districts/FeatureServer/0", "DISTRICT"),
}

# Precincts that are Army posts. Nobody there votes for a magistrate.
MILITARY = re.compile(r"^(fort|ft\.?)\s+(knox|campbell)\b", re.I)

MAPSHAPER = "mapshaper@0.6.102"
PRECISION = "0.000001"
SIMPLIFY = "interval=20"
FIDELITY_CEILING_M = 25.0
PAUSE = 0.5

# A county's districts must cover the county. Measured 2026-10-15 at 300 points
# a county; the posts are the only large undrawn ground, so the three counties
# that hold one carry their own floor, each a little under its measured share.
TILING_SAMPLES = 300
TILING_MIN_SAME = 0.96
TILING_FLOOR = {"Hardin": 0.80, "Bullitt": 0.75, "Christian": 0.88}

PREC = re.compile(r"^\s{0,3}([A-Z]\d{3})[A-Z]?(?:\s|$)")
HDR = re.compile(r"^\s*['‘’\"]?(?:(?:REP|DEM|Republican|Democratic)\s+)?"
                 r"(MAGISTRATE)\b[\s,\-]*(.*)$", re.I)
OCR_HEAD = re.compile(r"^\W{0,4}([A-Z])([0-9OIl|S]{3})[A-Z]?\b[^\n]{0,40}ballots\s*cast", re.M)
OCR_CONTEST = re.compile(r"(MAGISTRATE)\s+([^\n]*?)\s*-\s*\(Vote", re.I)
OCR_DIGITS = str.maketrans({"O": "0", "o": "0", "I": "1", "l": "1", "|": "1", "S": "5"})


def fail(msg):
    raise SystemExit("build-ky-county-districts: FATAL: %s" % msg)


def district_key(rest):
    import ky_fiscal_court_results_scraper as S  # noqa: PLC0415
    rest = rest.replace("2rd", "2nd").replace("3st", "3rd").replace("1nd", "1st")
    return S.district_key(rest)


# ---------- reading the sheets ----------
def parse_text(text):
    """A text-layer sheet -> {precinct: {districts}}. Each precinct's block runs
    from its code line to the next; every Magistrate heading inside it names a
    race on that precinct's ballot."""
    out = collections.defaultdict(set)
    cur = None
    for line in text.splitlines():
        m = PREC.match(line)
        if m:
            cur = m.group(1).upper()
            continue
        h = HDR.match(line)
        if h and cur:
            d = district_key(h.group(2))
            if d:
                out[cur].add(d)
    return out


def parse_ocr(text):
    """A scanned sheet read by tesseract. The precinct's own heading is a dark
    band recognition often loses, so the sheet is split at each precinct's
    first race (STRAIGHT PARTY) and a block counts only when exactly one
    precinct code is read inside it."""
    out = collections.defaultdict(set)
    for block in re.split(r"STRAIGHT\s+PARTY", text):
        codes = {m.group(1) + m.group(2).translate(OCR_DIGITS) for m in OCR_HEAD.finditer(block)}
        codes = {c for c in codes if re.fullmatch(r"[A-Z]\d{3}", c)}
        ds = {district_key(m.group(2)) for m in OCR_CONTEST.finditer(block)} - {None}
        if len(codes) == 1 and ds:
            out[codes.pop()] |= ds
    return out


def sheet_codes(text):
    return {m.group(1).upper() for line in text.splitlines() for m in [PREC.match(line)] if m}


class Reader:
    def __init__(self, cache):
        import requests  # noqa: PLC0415
        import scraper_common as sc  # noqa: PLC0415
        self.sc = sc
        self.headers = dict(sc.UA_HEADERS_ROSTER_BOT)
        self.session = requests.Session()
        self.cache = cache
        os.makedirs(cache, exist_ok=True)

    def get(self, url, **kw):
        self.sc.require_robots_once(url, self.headers["User-Agent"], headers=self.headers)
        time.sleep(PAUSE)
        r = self.session.get(url, headers=self.headers, timeout=180, **kw)
        r.raise_for_status()
        return r

    def links(self, page, folder):
        r = self.get(page)
        return sorted(set(urljoin(page, html.unescape(h)) for h in
                          re.findall(r'href="([^"]+%s/[^"]+\.pdf)"' % folder, r.text, re.I)))

    def sheet(self, url, tag):
        """(text, method) for one recap sheet, cached by election and file."""
        import ky_fiscal_court_results_scraper as S  # noqa: PLC0415
        name = re.sub(r"[^A-Za-z]", "", unquote(url.rsplit("/", 1)[1])[:-4])
        path = os.path.join(self.cache, "%s-%s.json" % (tag, name))
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                d = json.load(fh)
            return d["text"], d["method"]
        r = self.get(url)
        if not r.content.startswith(b"%PDF"):
            return None, None
        with tempfile.TemporaryDirectory() as tmp:
            pdf = os.path.join(tmp, "s.pdf")
            with open(pdf, "wb") as fh:
                fh.write(r.content)
            text, method = S.sheet_text(pdf, tmp)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"url": url, "text": text, "method": method}, fh)
        return text, method

    def features(self, url, out_fields, where="1=1", page=1000, order=None):
        feats, off = [], 0
        while True:
            params = dict(where=where, outFields=out_fields, outSR=4326, f="geojson",
                          geometryPrecision=6, resultOffset=off, resultRecordCount=page)
            if order:
                params["orderByFields"] = order
            r = self.get(url + "/query", params=params)
            j = r.json()
            if "error" in j:
                fail("%s answered an error envelope: %r" % (url, j["error"]))
            fs = j.get("features") or []
            feats += fs
            off += len(fs)
            more = (j.get("properties") or {}).get("exceededTransferLimit") or j.get("exceededTransferLimit")
            if not fs or not more:
                return feats

    def cached_json(self, name, fn):
        path = os.path.join(self.cache, name)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
        data = fn()
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        return data


def county_of_url(url):
    return re.sub(r"\s+County$", "", unquote(url.rsplit("/", 1)[1])[:-4]).strip()


def norm_county(name):
    return {"Mccreary": "McCreary", "Mclean": "McLean", "Mccracken": "McCracken",
            "Larue": "Larue", "LaRue": "Larue"}.get(name, name)


# ---------- placing precincts ----------
def map_number(props, field):
    m = re.search(r"\d+", str(props.get(field) or ""))
    return str(int(m.group())) if m else None


def assign(county, codes, names, ev26, ev22, sheet26, k_count, mapdist=None):
    """Place every precinct of one county. Returns (placement, sources, notes,
    undrawn) where placement maps a precinct to its district."""
    notes = []
    undrawn = {p: "an Army post: no magistrate race on its ballot"
               for p in codes if MILITARY.match(names.get(p) or "")}
    both = [p for p in ev26 if p in ev22 and len(ev26[p]) == 1 and len(ev22[p]) == 1
            and p in codes]
    disagree = [p for p in both if ev26[p] != ev22[p]]
    use22 = len(both) >= 2 and not disagree
    if ev22 and not use22:
        notes.append("2022 not used: %d precincts placed by both elections, %d disagree"
                     % (len(both), len(disagree)))
    place, src, bad = {}, {}, set()
    for tag, ev in (("2026 primary", ev26), ("2022 general", ev22 if use22 else {})):
        for p, ds in ev.items():
            if p not in codes or p in undrawn:
                continue
            if len(ds) != 1:
                bad.add(p)
                continue
            d = next(iter(ds))
            if p in place and place[p] != d:
                bad.add(p)
                continue
            place.setdefault(p, d)
            src.setdefault(p, tag)
    for p in bad:
        place.pop(p, None)
        src.pop(p, None)
    if bad:
        notes.append("two answers for %s" % ", ".join(sorted(bad)))
    rest = set(codes) - set(place) - set(undrawn)
    if rest and mapdist:
        wrong = [p for p in place if mapdist(p) != place[p]]
        if wrong:
            notes.append("the county's map disagrees with the ballots at %s, so it "
                         "places nothing" % ", ".join(sorted(wrong)))
        else:
            for p in sorted(rest):
                d = mapdist(p)
                if d:
                    place[p], src[p] = d, "county map"
            rest = set(codes) - set(place) - set(undrawn)
    if rest and k_count:
        empty = set(str(i) for i in range(1, k_count + 1)) - set(place.values())
        if len(empty) == 1 and rest <= sheet26:
            d = empty.pop()
            for p in rest:
                place[p], src[p] = d, "the one uncontested district"
            rest = set()
        elif len(empty) == 1:
            notes.append("%s not on the 2026 sheet" % ", ".join(sorted(rest - sheet26)))
    return place, src, notes, undrawn


def district_count(rec, contests22):
    """How many numbered districts a county has, where two sources agree: the
    directory's count of magistrates and the 2022 sheet's count of races."""
    n = len([m for m in rec["members"] if m.get("role") == "Magistrate"])
    d22 = {k.split("|")[1] for k in contests22 if k.startswith("MAGISTRATE|")}
    if d22 and all(x.isdigit() for x in d22) and len(d22) == n and max(map(int, d22)) == n:
        return n
    return None


# ---------- gathering ----------
def load_officials():
    with open(OFFICIALS, encoding="utf-8") as fh:
        return json.load(fh)


def load_results22():
    with open(RESULTS_2022, encoding="utf-8") as fh:
        return json.load(fh)["counties"]


def read_sheet(reader, url, tag):
    text, method = reader.sheet(url, tag)
    if text is None:
        return {}, set(), None
    if method == "ocr":
        ev = parse_ocr(text)
        return ev, set(ev), method
    return parse_text(text), sheet_codes(text), method


def county_map(reader, county, fabric_geo):
    """A function precinct -> district from the county's own map, by the
    precinct's representative point, or None where the map is not listed."""
    from shapely.geometry import shape  # noqa: PLC0415
    if county not in COUNTY_MAPS:
        return None
    url, field = COUNTY_MAPS[county]
    feats = reader.cached_json("map-%s.json" % county,
                               lambda: reader.features(url, field))
    polys = [(map_number(f["properties"], field), shape(f["geometry"]).buffer(0))
             for f in feats if f.get("geometry")]

    def where(p):
        g = fabric_geo.get(p)
        if g is None:
            return None
        pt = g.representative_point()
        hit = {d for d, s in polys if d and s.contains(pt)}
        return hit.pop() if len(hit) == 1 else None
    return where


def compose(reader, officials, results22, fabric):
    """Place every magistrate county's precincts. Returns (districts, report)
    where districts is [(fips, county, district, [precinct geometries])]."""
    from shapely.geometry import shape  # noqa: PLC0415
    by_county = collections.defaultdict(dict)
    names = collections.defaultdict(dict)
    for f in fabric:
        p = f["properties"]
        c = norm_county(p["CountyName"])
        if f.get("geometry"):
            by_county[c][p["PrecinctCode"]] = shape(f["geometry"]).buffer(0)
            names[c][p["PrecinctCode"]] = p.get("PrecinctName") or ""
    links26 = {norm_county(county_of_url(u)): u
               for u in reader.links(PRIMARY_PAGE, "PrimaryRecaps")}
    districts, report = [], {}
    for fips, rec in sorted(officials.items()):
        if rec["form"] != "magistrate":
            continue
        county = norm_county(rec["county"].replace(" County", ""))
        codes = set(by_county.get(county) or ())
        if not codes:
            fail("the precinct map carries no precincts for %s County" % county)
        ev26, sheet26, m26 = ({}, set(), None)
        if county in links26:
            ev26, sheet26, m26 = read_sheet(reader, links26[county], "p26")
        r22 = results22.get(county) or {}
        ev22, m22 = {}, None
        if r22.get("url"):
            ev22, _, m22 = read_sheet(reader, r22["url"], "g22")
        k = district_count(rec, r22.get("contests") or {})
        mapdist = county_map(reader, county, by_county[county])
        place, src, notes, undrawn = assign(county, codes, names[county], ev26, ev22,
                                            sheet26, k, mapdist)
        missing = sorted(codes - set(place) - set(undrawn))
        ds = sorted(set(place.values()), key=lambda s: (len(s), s))
        n_mag = len([m for m in rec["members"] if m.get("role") == "Magistrate"])
        d22 = {x.split("|")[1] for x in (r22.get("contests") or {}) if x.startswith("MAGISTRATE|")}
        if not missing and k is None and len(ds) != n_mag and set(ds) != d22:
            notes.append("%d districts placed, the directory lists %d magistrates and "
                         "2022 had %d races" % (len(ds), n_mag, len(d22)))
            missing = ["(district count)"]
        entry = {"fips": fips, "precincts": len(codes), "sheet2026": m26, "sheet2022": m22,
                 "placedBy": dict(collections.Counter(src.values())),
                 "notes": notes, "drawn": not missing}
        if undrawn:
            entry["leftOut"] = {p: "%s (%s)" % (why, names[county].get(p, ""))
                                for p, why in sorted(undrawn.items())}
        if missing:
            entry["unplaced"] = missing
        else:
            entry["districts"] = ds
            for d in ds:
                districts.append((fips, county, d, "magistrate",
                                  [by_county[county][p] for p in sorted(place) if place[p] == d]))
        report[county] = entry
    return districts, report, by_county


def councils(reader, by_county):
    """Louisville's and Lexington's council districts, each clipped to its
    county as the precinct map draws it so no line overlaps a neighbour's."""
    from shapely.geometry import shape  # noqa: PLC0415
    from shapely.ops import unary_union  # noqa: PLC0415
    out, seats = [], {}
    for fips, c in sorted(COUNCILS.items()):
        feats = reader.cached_json("council-%s.json" % fips, lambda c=c: reader.features(
            c["url"], "%s,%s" % (c["district"], c["name"])))
        if len(feats) != c["expect"]:
            fail("%s's council layer carries %d districts, expected %d"
                 % (c["county"], len(feats), c["expect"]))
        outline = unary_union(list(by_county[c["county"]].values())).buffer(0)
        seats[fips] = {}
        for f in feats:
            d = map_number(f["properties"], c["district"])
            name = re.sub(r"\s+", " ", str(f["properties"].get(c["name"]) or "")).strip()
            if not d or d in seats[fips]:
                fail("%s's council layer has a missing or repeated district %r" % (c["county"], d))
            seats[fips][d] = name
            geom = shape(f["geometry"]).buffer(0).intersection(outline)
            out.append((fips, c["county"], d, c["body"], [geom]))
    return out, seats


# ---------- geometry ----------
def dissolve(rows):
    from shapely.geometry import mapping, MultiPolygon, Polygon  # noqa: PLC0415
    from shapely.ops import unary_union  # noqa: PLC0415
    feats = []
    for fips, county, d, body, geoms in rows:
        g = unary_union(geoms).buffer(0)
        polys = [x for x in getattr(g, "geoms", [g]) if isinstance(x, Polygon) and not x.is_empty]
        g = polys[0] if len(polys) == 1 else MultiPolygon(polys)
        feats.append({"type": "Feature", "geometry": mapping(g), "properties": {
            "key": "%s-%s" % (fips, d), "county": county, "countyFips": fips,
            "district": d, "body": body}})
    feats.sort(key=lambda f: (f["properties"]["countyFips"],
                              (len(f["properties"]["district"]), f["properties"]["district"])))
    return {"type": "FeatureCollection", "features": json.loads(json.dumps(feats))}


def run_mapshaper(source_path, out_path):
    subprocess.run(["npx", "-y", MAPSHAPER, source_path, "-simplify", "dp", "keep-shapes",
                    SIMPLIFY, "-o", "precision=" + PRECISION, "format=geojson", out_path],
                   check=True, cwd=INSTANCE)


def _rings_of(geom):
    c = geom.get("coordinates") or []
    if geom.get("type") == "Polygon":
        return c
    if geom.get("type") == "MultiPolygon":
        return [ring for poly in c for ring in poly]
    return []


def _seg_index(feature, cell=0.02):
    idx = {}
    for ring in _rings_of(feature["geometry"]):
        for i in range(len(ring) - 1):
            a, b = ring[i], ring[i + 1]
            x0, x1 = sorted((a[0], b[0]))
            y0, y1 = sorted((a[1], b[1]))
            for gx in range(int(math.floor(x0 / cell)), int(math.floor(x1 / cell)) + 1):
                for gy in range(int(math.floor(y0 / cell)), int(math.floor(y1 / cell)) + 1):
                    idx.setdefault((gx, gy), []).append((a, b))
    return idx


def _point_to_segment_m(p, a, b):
    mx = 111320.0 * math.cos(math.radians(p[1]))
    px, py, ax, ay = p[0] * mx, p[1] * 111320.0, a[0] * mx, a[1] * 111320.0
    bx, by = b[0] * mx, b[1] * 111320.0
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    t = 0.0 if l2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / l2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def check_fidelity(src_features, drawn_features):
    """Worst distance from a source vertex to its own district as drawn: how
    far the true line strays from the line a reader sees."""
    drawn = {f["properties"]["key"]: f for f in drawn_features}
    worst, over = 0.0, []
    for f in src_features:
        d = drawn.get(f["properties"]["key"])
        if d is None:
            over.append(f["properties"]["key"] + " (lost)")
            continue
        idx = _seg_index(d)
        w = 0.0
        for ring in _rings_of(f["geometry"]):
            for v in ring[:-1]:
                gx, gy = int(math.floor(v[0] / 0.02)), int(math.floor(v[1] / 0.02))
                cand = []
                for ddx in (-1, 0, 1):
                    for ddy in (-1, 0, 1):
                        cand += idx.get((gx + ddx, gy + ddy), ())
                if cand:
                    w = max(w, min(_point_to_segment_m(v, a, b) for a, b in cand))
        worst = max(worst, w)
        if w > FIDELITY_CEILING_M:
            over.append(f["properties"]["key"])
    return worst, over


def _point_in_ring(pt, ring):
    x, y = pt
    inside, j = False, len(ring) - 1
    for i in range(len(ring)):
        xi, yi, xj, yj = ring[i][0], ring[i][1], ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _point_in_geometry(pt, geom):
    polys = [geom["coordinates"]] if geom["type"] == "Polygon" else (
        geom["coordinates"] if geom["type"] == "MultiPolygon" else [])
    for poly in polys:
        inside = False
        for ring in poly:
            if _point_in_ring(pt, ring):
                inside = not inside
        if inside:
            return True
    return False


def _bbox(geom):
    xs, ys = [], []
    for ring in _rings_of(geom):
        for x, y in ((v[0], v[1]) for v in ring):
            xs.append(x)
            ys.append(y)
    return [min(xs), min(ys), max(xs), max(ys)]


def _model(features):
    return [(f["properties"]["key"], f["properties"]["countyFips"], f["geometry"],
             _bbox(f["geometry"])) for f in features]


def _hits(model, pt):
    return [(k, c) for k, c, g, bb in model
            if bb[0] <= pt[0] <= bb[2] and bb[1] <= pt[1] <= bb[3]
            and _point_in_geometry(pt, g)]


STATE_BBOX = (-89.58, 36.49, -81.96, 39.15)


def validate(src_features, new_features, samples=2000, seed=2024):
    """The fleet's 2,000-point protocol: the simplified file answers as the
    dissolved source does at >= 99.5% of points, and no point is in two."""
    src, new = _model(src_features), _model(new_features)
    rng = random.Random(seed)
    agree = overlaps = 0
    for _ in range(samples):
        pt = (rng.uniform(STATE_BBOX[0], STATE_BBOX[2]), rng.uniform(STATE_BBOX[1], STATE_BBOX[3]))
        s = [k for k, _ in _hits(new, pt)]
        o = [k for k, _ in _hits(src, pt)]
        overlaps += len(s) > 1
        agree += (o[0] if len(o) == 1 else len(o)) == (s[0] if len(s) == 1 else len(s))
    pct = 100.0 * agree / samples
    if overlaps:
        return False, "%d of %d points fell in two districts" % (overlaps, samples)
    if pct < 99.5:
        return False, "agreement only %.2f%% (need 99.5%%)" % pct
    return True, "%d/%d (%.2f%%) agreement, no point in two districts" % (agree, samples, pct)


def check_tiling(features, seed=2026):
    """Points inside each DRAWN county (Census outline) must land in one of
    that county's own districts, and none in two."""
    with open(COUNTIES_FILE, encoding="utf-8") as fh:
        census = {c["properties"]["GEOID"]: c for c in json.load(fh)["features"]}
    model = _model(features)
    rng = random.Random(seed)
    problems, worst = [], []
    for fips in sorted({f["properties"]["countyFips"] for f in features}):
        c = census.get(fips)
        if c is None:
            problems.append("%s is not a Kentucky county" % fips)
            continue
        name = c["properties"]["NAME"]
        geom, bb = c["geometry"], _bbox(c["geometry"])
        same = other = none = n = tries = 0
        while n < TILING_SAMPLES and tries < TILING_SAMPLES * 50:
            tries += 1
            pt = (rng.uniform(bb[0], bb[2]), rng.uniform(bb[1], bb[3]))
            if not _point_in_geometry(pt, geom):
                continue
            n += 1
            hits = _hits(model, pt)
            if len(hits) > 1:
                problems.append("%s: %.5f,%.5f is in %s" % (name, pt[1], pt[0],
                                                            ", ".join(k for k, _ in hits)))
            if any(cf == fips for _, cf in hits):
                same += 1
            elif hits:
                other += 1
            else:
                none += 1
        floor = TILING_FLOOR.get(re.sub(r" County$", "", name), TILING_MIN_SAME)
        worst.append((same / float(n), name, same, other, none, n))
        if same < floor * n:
            problems.append("%s: %d of %d points land in its own districts (%d another "
                            "county's, %d none; floor %.2f)" % (name, same, n, other, none, floor))
        if other > 0.02 * n:
            problems.append("%s: %d of %d points land in another county's district"
                            % (name, other, n))
    worst.sort()
    w = worst[0]
    return problems, "tiling: %d counties; lowest own share %.3f (%s: %d own, %d other, %d none of %d)" % (
        len(worst), w[0], w[1], w[2], w[3], w[4], w[5])


def check_shipped(geo, record):
    problems = []
    officials = load_officials()
    feats = geo.get("features") or []
    keys = [f["properties"].get("key") for f in feats]
    if len(set(keys)) != len(keys):
        problems.append("a district key appears twice")
    per = collections.defaultdict(set)
    for f in feats:
        p = f["properties"]
        rec = officials.get(p.get("countyFips"))
        form = rec and rec["form"]
        want = {"magistrate": "magistrate", "metro": "metro", "urban-county": "urban-county"}.get(form)
        if p.get("body") != want:
            problems.append("%s carries body %r; the county's form is %r" % (p.get("key"), p.get("body"), form))
        if p.get("key") != "%s-%s" % (p.get("countyFips"), p.get("district")):
            problems.append("%s's key does not match its county and district" % p.get("key"))
        per[p.get("county")].add(p.get("district"))
    drawn = {c: set(v["districts"]) for c, v in record["counties"].items() if v.get("drawn")}
    for fips, c in COUNCILS.items():
        drawn[c["county"]] = {str(i) for i in range(1, c["expect"] + 1)}
    for county, want in sorted(drawn.items()):
        got = per.get(county, set())
        if got != want:
            problems.append("%s: the record names districts %s, the file carries %s"
                            % (county, ",".join(sorted(want)), ",".join(sorted(got)) or "none"))
    for county in sorted(set(per) - set(drawn)):
        problems.append("%s is drawn but the record does not say so" % county)
    return problems


# ---------- record ----------
def write_record(report, seats, shipped_bytes, fidelity, valid_msg):
    record = {
        "publisher": "Kentucky State Board of Elections (precincts and recap sheets); "
                     "LOJIC and the Lexington-Fayette Urban County Government (council maps)",
        "precincts": PRECINCTS,
        "sheets": {"2026 primary": PRIMARY_PAGE, "2022 general": GENERAL_PAGE},
        "countyMaps": {c: u for c, (u, _) in sorted(COUNTY_MAPS.items())},
        "councils": {f: c["url"] for f, c in sorted(COUNCILS.items())},
        "built": datetime.date.today().isoformat(),
        "shipped_sha256": hashlib.sha256(shipped_bytes).hexdigest(),
        "fidelityWorstM": round(fidelity, 1),
        "validate": valid_msg,
        "counties": report,
        "councilSeats": seats,
    }
    with open(RECORD, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=1, sort_keys=True, ensure_ascii=False)
        fh.write("\n")


def build(cache):
    reader = Reader(cache)
    fabric = reader.cached_json("precincts.json", lambda: reader.features(
        PRECINCTS, "StCoFIPS,CountyName,PrecinctCode,PrecinctName", page=500, order="OBJECTID"))
    if len(fabric) < 3000:
        fail("the precinct map returned %d precincts, expected about 3,193" % len(fabric))
    officials, results22 = load_officials(), load_results22()
    rows, report, by_county = compose(reader, officials, results22, fabric)
    crows, seats = councils(reader, by_county)
    src = dissolve(rows + crows)
    drawn = sorted(c for c, v in report.items() if v["drawn"])
    print("drawn %d of %d magistrate counties: %s" % (len(drawn), len(report), ", ".join(drawn)))
    for c, v in sorted(report.items()):
        if not v["drawn"]:
            print("  not drawn %-12s unplaced %s %s" % (c, " ".join(v.get("unplaced", [])[:8]),
                                                         "; ".join(v["notes"])))
    with tempfile.TemporaryDirectory() as tmp:
        sp, op = os.path.join(tmp, "src.geojson"), os.path.join(tmp, "out.geojson")
        with open(sp, "w") as fh:
            json.dump(src, fh)
        run_mapshaper(sp, op)
        with open(op) as fh:
            simp = json.load(fh)
    simp = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": f["properties"], "geometry": f["geometry"]}
        for f in simp["features"] if f.get("geometry")]}
    worst, over = check_fidelity(src["features"], simp["features"])
    print("fidelity: worst %.1f m (ceiling %.0f m)" % (worst, FIDELITY_CEILING_M))
    if over:
        fail("%d districts stray past %.0f m: %s" % (len(over), FIDELITY_CEILING_M, ", ".join(over[:10])))
    ok, msg = validate(src["features"], simp["features"])
    print("validate: " + msg)
    if not ok:
        fail(msg)
    problems, line = check_tiling(simp["features"])
    print(line)
    if problems:
        fail("; ".join(problems[:10]))
    raw = json.dumps(simp, separators=(",", ":")) + "\n"
    fake = {"counties": report}
    problems = check_shipped(simp, fake)
    if problems:
        fail("; ".join(problems[:10]))
    with open(OUT_FILE, "w", encoding="utf-8") as fh:
        fh.write(raw)
    write_record(report, seats, raw.encode(), worst, msg)
    print("wrote %s: %d districts in %d counties (%d bytes)"
          % (os.path.relpath(OUT_FILE, REPO), len(simp["features"]),
             len({f["properties"]["countyFips"] for f in simp["features"]}), len(raw)))


def check():
    with open(OUT_FILE, encoding="utf-8") as fh:
        raw = fh.read()
    with open(RECORD, encoding="utf-8") as fh:
        record = json.load(fh)
    geo = json.loads(raw)
    problems = check_shipped(geo, record)
    if hashlib.sha256(raw.encode()).hexdigest() != record.get("shipped_sha256"):
        problems.append("the shipped file does not hash to what the builder recorded; "
                        "rebuild it rather than editing it by hand")
    tiling, line = check_tiling(geo["features"])
    problems += tiling
    print(line)
    if problems:
        for p in problems:
            print("build-ky-county-districts: FAIL: " + p)
        raise SystemExit(1)
    print("build-ky-county-districts --check: OK: %d districts in %d counties, each county "
          "covered by its own districts" % (len(geo["features"]),
                                             len({f["properties"]["countyFips"] for f in geo["features"]})))


SELFTEST_TEXT = """
A101 NORTH
MAGISTRATE 1st Magisterial District - (Vote for One)
UNITED STATES SENATOR - (Vote for One)
A102 SOUTH
REP MAGISTRATE 2nd Magisterial District - (Vote for One)
"""
SELFTEST_OCR = """
A1O1 NORTH 120 ballots cast
MAGISTRATE 3rd Magisterial District - (Vote for One)
STRAIGHT PARTY
B201 WEST 80 ballots cast
B202 EAST 80 ballots cast
MAGISTRATE 1st Magisterial District - (Vote for One)
"""


def selftest():
    ev = parse_text(SELFTEST_TEXT)
    assert dict(ev) == {"A101": {"1"}, "A102": {"2"}}, ev
    assert sheet_codes(SELFTEST_TEXT) == {"A101", "A102"}
    ev = parse_ocr(SELFTEST_OCR)
    assert dict(ev) == {"A101": {"3"}}, ev  # the two-code block counts for nobody
    codes = {"A1", "A2", "B1", "B2", "C1"}
    names = {"C1": "Fort Knox 26"}
    ev26 = {"A1": {"1"}, "B1": {"2"}}
    ev22 = {"A1": {"1"}, "B1": {"2"}, "A2": {"1"}}
    place, src, notes, undrawn = assign("T", codes, names, ev26, ev22, {"A1", "B1", "B2"}, 3)
    assert undrawn == {"C1": "an Army post: no magistrate race on its ballot"}
    assert place == {"A1": "1", "B1": "2", "A2": "1", "B2": "3"}, place
    place, *_ = assign("T", codes, names, ev26, ev22, {"A1", "B1", "B2"}, 4)
    assert "B2" not in place  # two districts empty: nothing to infer
    # one district empty, the leftover on the 2026 sheet: it is that district
    place, src, notes, _ = assign("T", {"A1", "B1", "B2"}, {}, ev26, {}, {"A1", "B1", "B2"}, 3)
    assert place == {"A1": "1", "B1": "2", "B2": "3"} and src["B2"] == "the one uncontested district"
    # ... but not when a leftover is missing from the sheet
    place, _, notes, _ = assign("T", {"A1", "B1", "B2"}, {}, ev26, {}, {"A1", "B1"}, 3)
    assert "B2" not in place and any("not on the 2026 sheet" in n for n in notes)
    # 2022 disagreeing with 2026 is not used at all
    place, _, notes, _ = assign("T", {"A1", "B1", "A2"}, {}, ev26,
                                {"A1": {"2"}, "B1": {"2"}, "A2": {"1"}}, set(), None)
    assert "A2" not in place and notes[0].startswith("2022 not used")
    # a county map places leftovers only if it agrees with the ballots
    m = {"A1": "1", "B1": "2", "B2": "2"}.get
    place, src, _, _ = assign("T", {"A1", "B1", "B2"}, {}, ev26, {}, set(), None, m)
    assert place["B2"] == "2" and src["B2"] == "county map"
    m = {"A1": "2", "B1": "2", "B2": "2"}.get
    place, _, notes, _ = assign("T", {"A1", "B1", "B2"}, {}, ev26, {}, set(), None, m)
    assert "B2" not in place and "disagrees" in notes[0]
    # two answers for one precinct keep it unplaced
    place, _, notes, _ = assign("T", {"A1"}, {}, {"A1": {"1", "2"}}, {}, set(), None)
    assert not place and notes
    assert district_key("2rd Magisterial District") == "2"
    print("build-ky-county-districts --selftest: OK")


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n")[0])
    ap.add_argument("--check", action="store_true", help="offline: hold the shipped file to its record")
    ap.add_argument("--selftest", action="store_true", help="offline: the parsers and the placing rules")
    ap.add_argument("--cache", help="keep fetched sheets and maps here (default: a temporary directory)")
    args = ap.parse_args()
    if args.selftest:
        selftest()
    elif args.check:
        check()
    elif args.cache:
        build(args.cache)
    else:
        with tempfile.TemporaryDirectory() as tmp:
            build(tmp)


if __name__ == "__main__":
    main()
