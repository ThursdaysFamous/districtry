#!/usr/bin/env python3
"""
Check every county commission and school board map the General Assembly's
map office publishes against the precincts that voted in each district
contest, and write down which maps pass, which fail and which no contest has
tested: ga/data/source/county-map-check.json.

This is step 2 of the Georgia launch plan. Step 3 draws a county's districts
only from a map this record says passes, and gives every other map a gap
record. Like the boundary builders it is an occasional OPERATOR step, not a
weekly job: run it again when the office lists a new or changed county map,
and after an election, when there are new contests to test the maps with.

THE INPUTS, MEASURED 2026-10-30.

  The map office's page. www.legis.ga.gov/joint-office/reapportionment is one
  page whose script reads the office's listing from the General Assembly's
  data service (/api/Reapportionment/Page), through the token the page hands
  every visitor (see build_ga_legislature_roster.py, whose `api` this script
  calls). The listing names, county by county, the map each county commission
  and school board is elected from, as a zipped shapefile: 206 files, one per
  body per county, whose districts carry a DISTRICT field ("001", "002", ...;
  Crisp's commission "D1-1" .. "D2-3" for its posts within two districts,
  Rabun's school board "ZONE2" .. "ZONE5"). One record in some files has an
  empty DISTRICT and covers the rest of the state; it is not a district.
  Four counties publish a second file for their "super districts": DeKalb's
  commission, Harris's school board, Lowndes's commission and Augusta-
  Richmond's commission.

  The office's statewide precinct map for 2024 (gaprec_2024-website-
  shapefile.zip, 2,724 precincts). Each precinct carries a DISTRICT code (the
  county's three-digit FIPS code and the precinct's own id) and, for all but
  27, its county and name; those 27 (Fulton's split precincts such as
  121SC21A, and the precincts on Fort Stewart, Fort Moore and Fort Pulaski)
  are given theirs from the DISTRICT code. It is the newest statewide
  precinct map the office lists; a newer one is reported, never used
  silently, because the contests have to be read against the precincts they
  were counted in.

  The Secretary of State's results site, results.sos.ga.gov (robots.txt
  answers 404: no policy, allow all). For each county and election,
  /results/public/api/elections/<county>/<election>/data lists the ballot
  items with the number of precincts each was counted in, and every precinct
  with the ballots cast there; /data/ballot-item/<id> lists the precincts that
  voted in one contest, with each one's votes. Three elections hold district
  contests for these boards: the general election of 5 November 2024, the
  general primary and nonpartisan election of 19 May 2026 (each party's
  primary is a contest of its own) and the primary runoff of 16 June 2026.
  The site carries no county contests for May 2024, when half the
  nonpartisan school boards were elected, so those seats are tested only by
  their 2026 contests or not at all. sos.ga.gov itself answers robots.txt
  with a challenge page and is not read.

  Census 2020 blocks with people in them, from TIGERweb
  (Tracts_Blocks/MapServer/12): 165,333 blocks holding 10,711,908 people,
  each placed at its internal point. Each county's blocks are checked against
  the service's own count and population sum for that county before use.

THE TEST. A county's map passes where every precinct that voted for District
2 lies inside District 2 on the map, and so on for each district.

Pairing the precincts. The results site names precincts by polling place,
the precinct map by name and id, and the two spell them differently, so the
November 2024 ballot's names are paired with the precinct map county by
county by scoring the names and ids and taking the best pairs first. A pair
scoring under 0.75 is a WEAK pair. The 2026 ballots are paired through the
2024 ballot: a precinct keeps its November 2024 pair only if its name is on
both ballots and its registered voters moved by no more than 20% against its
county's own change, because a precinct can gain or lose ground without a
rename (precincts_moved says what that was measured on). A new or changed
precinct is left unpaired. The June runoff's results carry no turnout by
precinct, so the May primary's stands in for it where the two ballots list
the same precincts.

Then, for each district contest:

  - Countywide: counted in every precinct of the county. The district is a
    residency district and the seat is elected at large; the contest says
    nothing about the map's lines.
  - Untestable: more than 5% of the contest's votes come from unpaired
    precincts. The record says whether those precincts changed after the
    precinct map ("precincts-changed") or never paired with it ("names":
    Long County's November 2024 precincts share no name with the map's).
  - At large across a school system: the contest's ballots are at least 60%
    of the ballots cast in the precincts the map covers. Gordon's and
    Whitfield's school boards elect seats this way, voted in every precinct
    of a school system smaller than its county.
  - Fails, forward: a precinct that voted in the contest with at least 20
    votes, and at least a tenth of its ballots, while the map puts less than
    1% of its area and less than 1% of its people in the district. The vote
    floor is there because a precinct can cast a few votes in a district it
    barely touches, from a handful of voters given that ballot.
  - Fails, reverse: a precinct of at least 100 people, at least half of them
    in the district on the map, that cast at least 50 ballots and did not
    vote in the contest. People and not area, because a large empty precinct
    of marsh or water can lie mostly in a district nobody there votes in
    (two of Chatham's, measured).
  - Untestable, weak match: the only evidence of a failure comes from weak
    pairs. A wrong pair is far likelier to put a precinct in the wrong
    district than in the right one, so a weak pair can pass a contest and
    cannot fail one.
  - Passes otherwise.

A failure on a 2026 ballot is recorded as a CONFLICT, not a failure, because
the precinct map is 2024's and a precinct can move without a rename or a
change in its registered voters large enough to show.

A district's status is the first of fail, conflict, pass, at-large,
untestable and countywide that any of its contests has, else untested. A
map's verdict is FAILS if any district failed; else CONFLICTS if any
conflicted; else PASSES if any passed (the record says which districts no
contest tested); else AT-LARGE, UNTESTABLE or VOTED-COUNTYWIDE by the same
order; else UNTESTED, for want of any contest. Contests that test no
district are recorded against the map without changing its verdict: a chair,
an at-large seat, Baker's seats named by place rather than number, and posts
numbered on a different scheme from the map's (Rabun's school board), all
voted county-wide (`no_district`); and a contest by district naming a
district the map does not have (`off_map`), because a board with more
districts than its map has moved on from it.

Usage:
    python3 ga/scripts/check_ga_county_maps.py --cache DIR [--out PATH]
    python3 ga/scripts/check_ga_county_maps.py --cache DIR --offline [--out PATH]
    python3 ga/scripts/check_ga_county_maps.py --check [PATH]

DIR holds everything fetched (about 450 MB on 2026-10-30, most of it the
precinct-by-precinct results) and the measurements, so a second run reads it
back. --offline fetches nothing and stops at the first missing input.
--check reads the record alone and confirms that every map's verdict follows
from its districts and every district's from its contests, without the
network or any geometry library.
"""

import argparse
import collections
import datetime
import difflib
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.parse
import zipfile

_HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE_ROOT = os.path.dirname(_HERE)
for _d in (_HERE, os.path.join(os.path.dirname(INSTANCE_ROOT), "scripts")):
    if _d not in sys.path:
        sys.path.append(_d)
from robots_policy import HostPacer, RobotsGate  # noqa: E402  (FLEET_SHARED)

USER_AGENT = "districtry/1.0 (+https://districtry.com/ga/)"
MIN_PACE_SECONDS = 1.0
ATTEMPTS = 4
RETRY_SECONDS = 3.0

DEFAULT_OUT = os.path.join(INSTANCE_ROOT, "data", "source", "county-map-check.json")
OFFICE_PAGE = "https://www.legis.ga.gov/joint-office/reapportionment"
RESULTS_API = "https://results.sos.ga.gov/results/public/api/elections/"
BLOCKS = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
          "Tracts_Blocks/MapServer/12/query")
PRECINCT_MAP_RE = re.compile(r"/precincts/gaprec_(\d{4})[^/?\"]*\.zip")
PRECINCT_MAP_YEAR = "2024"
STATE_FIPS = "13"
ELECTIONS = (
    ("2024NovGen", "2024-11-05", "General election"),
    ("GeneralPrimary51926", "2026-05-19", "General primary and nonpartisan election"),
    ("06162026GeneralPrimaryRunoff", "2026-06-16", "General primary runoff"),
)
# The runoff's results carry no turnout by precinct (measured 2026-10-30: an
# empty voterTurnout in all 159 counties), so where its precincts are the
# primary's, the primary's ballots and registrations stand in for them.
TURNOUT_FROM = {"06162026GeneralPrimaryRunoff": "GeneralPrimary51926"}

# The test's thresholds, explained in the module docstring.
UNMATCHED_MAX = 0.05
AT_LARGE_SHARE = 0.6
FORWARD_SHARE = 0.01
FORWARD_VOTES = 20
FORWARD_BALLOT_SHARE = 0.1
REVERSE_SHARE = 0.5
REVERSE_PEOPLE = 100
REVERSE_BALLOTS = 50
STRONG_MATCH = 0.75
PRECINCT_MAP_ELECTION = "2024NovGen"
REG_DRIFT = 0.2

BODIES = {"commission": "County Commission", "school-board": "School Board"}

_SESSION = None
_GATE = None
_PACER = None
_LAST = {}
OFFLINE = False


# --------------------------------------------------------------- fetching

def session():
    global _SESSION, _GATE, _PACER
    if _SESSION is None:
        import requests

        _SESSION = requests.Session()
        _SESSION.headers["User-Agent"] = USER_AGENT
        _GATE = RobotsGate(_SESSION, USER_AGENT)
        _PACER = HostPacer(_GATE)
    return _SESSION


def fetch(url, binary=False, accept=None):
    """The body at `url`, or None for a 404, after robots.txt allows it."""
    import requests

    if OFFLINE:
        raise SystemExit("FAIL: --offline and the cache holds no copy of %s" % url)
    s = session()
    ok, why = _GATE.allows(url)
    host = urllib.parse.urlsplit(url).netloc
    if host not in _LAST:
        print("robots.txt %s: %s" % (host, why), file=sys.stderr)
        _LAST[host] = 0.0
    if not ok:
        raise SystemExit("FAIL: robots.txt refuses %s (%s)" % (url, why))
    last = None
    for attempt in range(ATTEMPTS):
        if attempt:
            time.sleep(RETRY_SECONDS * attempt)
        wait = MIN_PACE_SECONDS - (time.time() - _LAST[host])
        if wait > 0:
            time.sleep(wait)
        try:
            with _PACER.hold(url):
                resp = s.get(url, timeout=300,
                             headers={"Accept": accept} if accept else {})
            _LAST[host] = time.time()
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.content if binary else resp.content.decode("utf-8")
        except (requests.RequestException, UnicodeDecodeError) as exc:
            _LAST[host] = time.time()
            last = exc
            print("  retrying %s (%s)" % (url, exc), file=sys.stderr)
    raise SystemExit("FAIL: %s did not answer after %d attempts (%s)" % (url, ATTEMPTS, last))


def cached(path, url, binary=False, accept=None):
    """Read `path`, or fetch `url` into it. A 404 is cached as an empty file."""
    if os.path.exists(path):
        with open(path, "rb") as fh:
            data = fh.read()
    else:
        body = fetch(url, binary=binary, accept=accept)
        data = b"" if body is None else (body if binary else body.encode("utf-8"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path + ".part", "wb") as fh:
            fh.write(data)
        os.replace(path + ".part", path)
    if not data:
        return None
    return data if binary else data.decode("utf-8")


def cached_json(path, url):
    text = cached(path, url, accept="application/json")
    return json.loads(text) if text else None


def office_page(cache):
    path = os.path.join(cache, "office-page.json")
    if not os.path.exists(path):
        if OFFLINE:
            raise SystemExit("FAIL: --offline and %s is missing" % path)
        import build_ga_legislature_roster as legis

        page = legis.api("Reapportionment/Page")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(page, fh, ensure_ascii=False, indent=1)
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def county_maps(page):
    """Every county map the office lists, as dicts naming its bodies."""
    out = []
    for county in page["counties"]:
        for res in county.get("countyResources") or []:
            category = res["name"].strip()
            bodies = [b for b, word in BODIES.items() if word in category]
            if not bodies:
                continue
            for f in res.get("resourceFiles") or []:
                if f.get("extension") != ".zip":
                    continue
                out.append({"county": county["name"].strip(), "category": category,
                            "title": f["title"].strip(), "url": f["url"],
                            "file": urllib.parse.urlsplit(f["url"]).path.rsplit("/", 1)[1],
                            "bodies": bodies, "super": "Super" in category})
    if len(out) < 200:
        raise SystemExit("FAIL: the office's page lists %d county maps; 206 were "
                         "listed on 2026-10-30, so its layout has probably changed" % len(out))
    return out


def precinct_map_url(page):
    found = {}
    for url in re.findall(r"https?://[^\"\s]+", json.dumps(page)):
        m = PRECINCT_MAP_RE.search(url)
        if m:
            found[m.group(1)] = url
    if PRECINCT_MAP_YEAR not in found:
        raise SystemExit("FAIL: the office's page no longer lists its %s precinct map"
                         % PRECINCT_MAP_YEAR)
    newer = sorted(y for y in found if y > PRECINCT_MAP_YEAR)
    if newer:
        print("NOTE: the office now lists a statewide precinct map for %s. This run "
              "still reads the %s map; a person decides when the contests tested "
              "have moved onto the newer one." % (", ".join(newer), PRECINCT_MAP_YEAR),
              file=sys.stderr)
    return found[PRECINCT_MAP_YEAR]


# --------------------------------------------------------------- geometry

def _projector():
    from pyproj import Transformer

    return Transformer.from_crs("EPSG:4269", "EPSG:5070", always_xy=True).transform


def read_zip(data, project):
    """[(record, shapely geometry in EPSG:5070)] for every shape in the zip."""
    import shapefile
    from shapely.geometry import shape
    from shapely.ops import transform
    from shapely.validation import make_valid

    z = zipfile.ZipFile(io.BytesIO(data))
    names = {n.lower(): n for n in z.namelist()}
    stems = [n[:-4].lower() for n in z.namelist() if n.lower().endswith(".shp")]
    if len(stems) != 1:
        raise SystemExit("FAIL: expected one shapefile in the zip, found %d" % len(stems))
    stem = stems[0]
    reader = shapefile.Reader(shp=io.BytesIO(z.read(names[stem + ".shp"])),
                              dbf=io.BytesIO(z.read(names[stem + ".dbf"])),
                              shx=io.BytesIO(z.read(names[stem + ".shx"])))
    out = []
    for sr in reader.iterShapeRecords():
        if not sr.shape.points:
            continue
        g = transform(project, shape(sr.shape.__geo_interface__))
        if not g.is_valid:
            g = make_valid(g)
        out.append((sr.record.as_dict(), g))
    return out


def county_key(name):
    return re.sub(r"[^a-z]", "", name.lower().replace(" county", ""))


def load_precincts(data, project):
    """{precinct code: {fips, county, id, name, geom}} from the statewide map."""
    recs = read_zip(data, project)
    names = {}
    for rec, _ in recs:
        if str(rec.get("CTYNAME", "")).strip():
            names[str(rec["FIPS"]).strip()] = str(rec["CTYNAME"]).strip()
    out = {}
    for rec, g in recs:
        code = str(rec["DISTRICT"]).strip()
        fips = str(rec.get("FIPS", "")).strip() or STATE_FIPS + code[:3]
        pid = str(rec.get("PRECINCT_I", "")).strip() or code[3:]
        out[code] = {"fips": fips, "county": names[fips], "id": pid,
                     "name": str(rec.get("PRECINCT_N", "")).strip() or pid, "geom": g}
    if len(out) < 2500:
        raise SystemExit("FAIL: the precinct map holds %d precincts; 2,724 on 2026-10-30" % len(out))
    return out


def fetch_blocks(cache):
    """{county FIPS3: [[GEOID, lon, lat, people]]}, checked against the service."""
    stats = json.dumps([
        {"statisticType": "sum", "onStatisticField": "POP100", "outStatisticFieldName": "pop"},
        {"statisticType": "count", "onStatisticField": "OBJECTID", "outStatisticFieldName": "n"}])
    q = {"where": "STATE='%s' AND POP100>0" % STATE_FIPS, "groupByFieldsForStatistics": "COUNTY",
         "outStatistics": stats, "f": "json"}
    summary = cached_json(os.path.join(cache, "blocks", "_counties.json"),
                          BLOCKS + "?" + urllib.parse.urlencode(q))
    if not summary or "error" in summary:
        raise SystemExit("FAIL: TIGERweb's block summary answered %r" % (summary,))
    want = {f["attributes"]["COUNTY"]: (int(f["attributes"]["pop"]), int(f["attributes"]["n"]))
            for f in summary["features"]}
    out = {}
    for c in sorted(want):
        rows, off = [], 0
        while True:
            q = {"where": "STATE='%s' AND COUNTY='%s' AND POP100>0" % (STATE_FIPS, c),
                 "outFields": "GEOID,INTPTLAT,INTPTLON,POP100", "returnGeometry": "false",
                 "orderByFields": "GEOID", "resultOffset": off, "resultRecordCount": 20000,
                 "f": "json"}
            d = cached_json(os.path.join(cache, "blocks", "%s-%d.json" % (c, off)),
                            BLOCKS + "?" + urllib.parse.urlencode(q))
            if not d or "error" in d:
                raise SystemExit("FAIL: TIGERweb answered %r for county %s" % (d, c))
            fs = d.get("features") or []
            rows += [[f["attributes"]["GEOID"], float(f["attributes"]["INTPTLON"]),
                      float(f["attributes"]["INTPTLAT"]), int(f["attributes"]["POP100"])]
                     for f in fs]
            if len(fs) < 20000 and not d.get("exceededTransferLimit"):
                break
            off += len(fs)
        got = (sum(r[3] for r in rows), len(rows))
        if got != want[c]:
            raise SystemExit("FAIL: county %s blocks %s, the service's own count %s"
                             % (c, got, want[c]))
        out[c] = rows
    return out


def locate(polys, pts):
    """For each (x, y) in pts, the key of the first of polys holding it, or None."""
    from shapely.geometry import Point
    from shapely.prepared import prep
    from shapely.strtree import STRtree

    tree = STRtree([g for _, g in polys])
    preps = [prep(g) for _, g in polys]
    out = []
    for x, y in pts:
        p = Point(x, y)
        hit = None
        for i in tree.query(p):
            if preps[i].contains(p) or polys[i][1].touches(p):
                hit = polys[i][0]
                break
        out.append(hit)
    return out


def measure(cache, maps, precinct_zip):
    """Area and people of each precinct in each district of each map.

    Each map's measurement is cached under the hash of its zip and of the
    precinct map, so a changed file is measured again and nothing else is.
    """
    project = _projector()
    psha = hashlib.sha256(precinct_zip).hexdigest()
    precincts = load_precincts(precinct_zip, project)
    by_fips = collections.defaultdict(list)
    for code, p in precincts.items():
        by_fips[p["fips"]].append((code, p["geom"]))
    blocks = None
    located = {}
    ppath = os.path.join(cache, "measure", "precincts-%s.json" % psha[:16])
    if os.path.exists(ppath):
        with open(ppath) as fh:
            pinfo = json.load(fh)
    else:
        blocks = fetch_blocks(cache)
        pinfo = {}
        for code, p in precincts.items():
            pinfo[code] = {"fips": p["fips"], "county": p["county"], "id": p["id"],
                           "name": p["name"], "area": p["geom"].area, "people": 0}
        for fips, rows in sorted(blocks.items()):
            pts = [project(lon, lat) for _, lon, lat, _ in rows]
            where = locate(by_fips[STATE_FIPS + fips], pts)
            located[fips] = (rows, pts, where)
            for row, w in zip(rows, where):
                if w is not None:
                    pinfo[w]["people"] += row[3]
        os.makedirs(os.path.dirname(ppath), exist_ok=True)
        with open(ppath, "w") as fh:
            json.dump(pinfo, fh)
    name_fips = {county_key(p["county"]): p["fips"] for p in pinfo.values()}
    for m in maps:
        m["fips"] = name_fips.get(county_key(m["county"]))
        if m["fips"] is None:
            raise SystemExit("FAIL: no precinct map county for %s" % m["county"])
        path = os.path.join(cache, "maps", m["file"])
        data = cached(path, m["url"], binary=True)
        if data is None:
            raise SystemExit("FAIL: %s answered 404" % m["url"])
        m["sha256"] = hashlib.sha256(data).hexdigest()
        mpath = os.path.join(cache, "measure", "%s-%s.json" % (m["sha256"][:16], psha[:16]))
        if os.path.exists(mpath):
            with open(mpath) as fh:
                m["measure"] = json.load(fh)
            continue
        dists = [(str(r.get("DISTRICT", "")).strip(), g) for r, g in read_zip(data, project)]
        dists = [(k, g) for k, g in dists if k]
        if not dists:
            raise SystemExit("FAIL: %s holds no DISTRICT values" % m["file"])
        area = collections.defaultdict(dict)
        darea = collections.Counter()
        for k, dg in dists:
            darea[k] += dg.area
            for code, pg in by_fips[m["fips"]]:
                if pg.intersects(dg):
                    a = pg.intersection(dg).area
                    if a > 0:
                        area[code][k] = area[code].get(k, 0.0) + a
        if blocks is None:
            blocks = fetch_blocks(cache)
        c3 = m["fips"][2:]
        if c3 not in located:
            rows = blocks[c3]
            pts = [project(lon, lat) for _, lon, lat, _ in rows]
            located[c3] = (rows, pts, locate(by_fips[m["fips"]], pts))
        rows, pts, where = located[c3]
        people = collections.defaultdict(collections.Counter)
        outside = 0
        for row, w, d in zip(rows, where, locate(dists, pts)):
            if w is None:
                continue
            if d is None:
                outside += row[3]
            else:
                people[w][d] += row[3]
        m["measure"] = {"district_area": dict(darea), "area": area,
                        "people": {k: dict(v) for k, v in people.items()},
                        "people_outside": outside}
        os.makedirs(os.path.dirname(mpath), exist_ok=True)
        with open(mpath, "w") as fh:
            json.dump(m["measure"], fh)
        print("  measured %s: %d districts" % (m["file"], len(darea)), file=sys.stderr, flush=True)
    return pinfo, psha


# --------------------------------------------------------------- matching

ABBR = {"CH": "CHURCH", "CHR": "CHURCH", "CHU": "CHURCH", "ELEM": "ELEMENTARY",
        "EL": "ELEMENTARY", "ES": "ELEMENTARY", "MS": "MIDDLE", "HS": "HIGH", "MT": "MOUNT",
        "BAPT": "BAPTIST", "BAP": "BAPTIST", "METH": "METHODIST", "COMM": "COMMUNITY",
        "CTR": "CENTER", "CNTR": "CENTER", "REC": "RECREATION", "SR": "SENIOR", "FD": "FIRE",
        "VFD": "FIRE", "STA": "STATION", "SCH": "SCHOOL", "SCHL": "SCHOOL", "LIB": "LIBRARY",
        "UMC": "METHODIST", "N": "NORTH", "S": "SOUTH", "E": "EAST", "W": "WEST", "ST": "SAINT",
        "CO": "COUNTY", "HTS": "HEIGHTS", "BLDG": "BUILDING", "GYM": "GYMNASIUM", "PK": "PARK",
        "AVE": "AVENUE", "RD": "ROAD", "VOL": "VOLUNTEER", "PRES": "PRESBYTERIAN",
        "EPIS": "EPISCOPAL", "CATH": "CATHOLIC", "ASSEM": "ASSEMBLY", "CT": "COURT",
        "CTHSE": "COURTHOUSE", "GOVT": "GOVERNMENT", "ADMIN": "ADMINISTRATION", "LK": "LAKE",
        "SPRGS": "SPRINGS", "SPGS": "SPRINGS", "FT": "FORT", "JR": "JUNIOR", "MID": "MIDDLE",
        "PCT": "", "PRECINCT": "", "PREC": ""}


def norm(s):
    s = re.sub(r"\([^)]*\)", " ", s)
    s = s.upper().replace("&", " AND ").replace("'", "").replace("’", "")
    toks = []
    for t in re.sub(r"[^A-Z0-9]+", " ", s).split():
        if t.isdigit():
            t = str(int(t))
        t = ABBR.get(t, t)
        if t:
            toks.append(t)
    return toks


def _bare(s):
    return re.sub(r"[^A-Z0-9]", "", s.upper()).lstrip("0") or "0"


def score(result_name, map_id, map_name):
    """How well a results-site precinct name fits one precinct on the map."""
    rn, mn = norm(result_name), norm(map_name)
    mid = _bare(map_id)
    if rn == mn or _bare(result_name) in (mid, _bare(map_name)):
        return 1.0      # the same name, or "02-Town" and "02TOWN"
    # "02-Town" or "0201 SHADY GROVE": a leading code that is the map's id
    first = re.split(r"[\s-]+", result_name.strip())[0]
    if len(result_name.split()) > 1 and any(c.isdigit() for c in first) and _bare(first) == mid:
        return 0.98
    if not rn or not mn:
        return 0.0
    penalty = 1.0
    # "Town A" and "Town B", or "1 Smyrna" and "2 Smyrna", are different precincts
    if rn[-1] != mn[-1] and len(rn[-1]) <= 3 and len(mn[-1]) <= 3:
        penalty = 0.4
    elif rn[0].isdigit() and mn[0].isdigit() and rn[0] != mn[0]:
        penalty = 0.4
    a, b = " ".join(rn), " ".join(mn)
    if (a.startswith(b) or b.startswith(a)) and min(len(a), len(b)) >= 4:
        return 0.9 * penalty
    hit, used = 0, set()
    for t in rn:
        for j, u in enumerate(mn):
            if j in used:
                continue
            if t == u or (min(len(t), len(u)) >= 3 and (t.startswith(u) or u.startswith(t))):
                hit += 1
                used.add(j)
                break
    tok = 2.0 * hit / (len(rn) + len(mn))
    if hit == len(rn) and any(len(t) >= 4 for t in rn):
        tok = max(tok, 0.75)
    return penalty * max(0.85 * tok, 0.8 * difflib.SequenceMatcher(None, a, b).ratio())


def match(result_names, map_precincts):
    """{results name: (precinct code, score)}, best pairs first, one to one."""
    got, taken = {}, set()
    for floor in (0.5, 0.35):
        pairs = []
        for r in result_names:
            if r in got:
                continue
            for code, p in map_precincts.items():
                if code in taken:
                    continue
                s = score(r, p["id"], p["name"])
                if s >= floor:
                    pairs.append((s, r, code))
        pairs.sort(key=lambda x: (-x[0], x[1], x[2]))
        for s, r, code in pairs:
            if r in got or code in taken:
                continue
            got[r] = (code, s)
            taken.add(code)
    left_r = [r for r in result_names if r not in got]
    left_m = [c for c in map_precincts if c not in taken]
    if len(left_r) == 1 and len(left_m) == 1:
        got[left_r[0]] = (left_m[0], 0.3)   # the one left on each side
    return got


# --------------------------------------------------------------- contests

# "Commisson", "Comission" and "Commmission" all occur in contest names.
BODY_CC = re.compile(r"com+is+i?on|\bBOC\b", re.I)
BODY_SB = re.compile(r"\bBOE\b|board of education|school board|board of ed\b|bd of ed", re.I)
NOT_CC = re.compile(r"tax com+is+i?on|water|soil|hospital|authority|public service", re.I)
# Statewide offices, and the questions the results site files as candidate contests.
NOT_A_SEAT = re.compile(r"commissioner of (agriculture|insurance|labor)|state school superintendent"
                        r"|\bE?SPLOST\b|\bbond\b|referendum|question", re.I)
PARTY = re.compile(r"\s*[-(]\s*(Rep|Dem|Republican|Democrat|Democratic|NP|Nonpartisan)\)?\s*$", re.I)
DIST = re.compile(r"(?:district|dist\.?|\bD|post|seat|zone)\s*#?\s*0*(\d+)", re.I)
POST = re.compile(r"post\s*#?\s*0*(\d+)", re.I)
# Columbus-Muscogee's council is its county commission.
COUNCIL_IS_COMMISSION = {"muscogee"}


def parse(name, ckey):
    """{body, district, post, super} for a county board contest, else None."""
    if NOT_A_SEAT.search(name):
        return None
    council = ckey in COUNCIL_IS_COMMISSION and re.search(r"council", name, re.I) \
        and not re.search(r"\bcity of\b", name, re.I)
    if BODY_SB.search(name):
        body = "school-board"
    elif (BODY_CC.search(name) and not NOT_CC.search(name)) or council:
        body = "commission"
    else:
        return None
    if body == "commission" and not council and re.search(r"\bcity\b|council|mayor", name, re.I):
        return None
    sup = bool(re.search(r"super|\bat[- ]large\b", name, re.I))
    core = PARTY.sub("", name)
    m = DIST.search(core) or re.search(r"\b0*(\d{1,2})-[A-Z]\b", core) \
        or re.search(r"\b0*(\d{1,2})\s*$", core)
    if not m:
        return {"body": body, "district": None, "post": None, "super": sup}
    post = POST.search(core)
    return {"body": body, "district": int(m.group(1)), "super": sup,
            "post": int(post.group(1)) if post and post.start() != m.start() else None}


def district_key(m, contest):
    """The DISTRICT value on map `m` a contest names, or None."""
    keys = {(int(k) if k.isdigit() else k): k for k in m["measure"]["district_area"]}
    if contest["district"] in keys:
        return keys[contest["district"]]
    alt = "D%s-%s" % (contest["district"], contest["post"])   # Crisp's posts
    return alt if alt in keys else None


def text(field):
    return field[0]["text"] if field else ""


def read_results(cache):
    """Every county board contest on the three ballots, with its precincts,
    and each county's precincts on each ballot with their ballots cast and
    registered voters: ({(election, county): {name: [ballots, registered]}},
    [contest])."""
    page = cached_json(os.path.join(cache, "results", "Georgia.json"),
                       RESULTS_API + "Georgia/2024NovGen/data")
    counties = page["jurisdiction"]["childLocalities"]
    if len(counties) != 159:
        raise SystemExit("FAIL: the results site lists %d counties, not 159" % len(counties))
    turnout, out = {}, []
    for el, day, label in ELECTIONS:
        for c in counties:
            sn = c["shortName"]
            ckey = county_key(sn.replace("-county-ga", "").replace("-", " "))
            d = cached_json(os.path.join(cache, "results", el, sn, "data.json"),
                            RESULTS_API + "%s/%s/data" % (sn, el))
            if not d:
                raise SystemExit("FAIL: no %s results for %s" % (el, sn))
            names = [text(p["name"]) for p in d.get("precincts") or [] if not p.get("isVirtual")]
            rows = {t.get("precinctName"): [t.get("ballotsCast") or 0, t.get("voterRegistration") or 0]
                    for t in d.get("voterTurnout") or []}
            prior = turnout.get((TURNOUT_FROM.get(el), ckey))
            if not rows and prior is not None and set(prior) == set(names):
                rows = prior
            turnout[(el, ckey)] = {n: rows.get(n, [0, 0]) for n in names}
            for bi in d.get("ballotItems") or []:
                if bi.get("contestType") != "Candidate":
                    continue
                name = text(bi["name"])
                pr = parse(name, ckey)
                if not pr:
                    continue
                units = (bi.get("reportingStatus") or {}).get("totalUnits")
                rec = dict(pr, election=el, county=ckey, name=name, units=units)
                if units is not None and units >= len(names):
                    rec["countywide"] = True
                else:
                    item = cached_json(os.path.join(cache, "results", el, sn, "items",
                                                    bi["id"] + ".json"),
                                       RESULTS_API + "%s/%s/data/ballot-item/%s" % (sn, el, bi["id"]))
                    rec["voted"] = {text(b["precinct"]["name"]): b.get("voteTotal") or 0
                                    for b in item["ballotItemWithBreakdown"]["breakdownResults"]
                                    if not b["precinct"].get("isVirtual")}
                out.append(rec)
        print("  read %s for 159 counties" % el, file=sys.stderr, flush=True)
    return turnout, out


# --------------------------------------------------------------- the test

def test_contest(c, m, dkey, matched, pinfo, ballots, moved):
    """The verdict on one district contest against one map, with its evidence.

    `matched` pairs the ballot's precinct names with the map's; `ballots` is
    each name's ballots cast; `moved` names the precincts whose ground
    changed after the precinct map, which are left unpaired.

    A precinct paired by a weak match (score under STRONG_MATCH) can pass a
    contest but cannot fail one: a wrong pairing is far likelier to put a
    precinct in the wrong district than in the right one, so evidence of a
    failure that rests on one is set aside as `weak` and the contest is
    untestable rather than failed.
    """
    meas = m["measure"]
    votes = c["voted"]
    total = sum(votes.values()) or 1
    unmatched = sorted(v for v in votes if v not in matched)
    um_share = sum(votes[v] for v in unmatched) / total
    out = {"precincts_voted": len(votes), "votes": sum(votes.values())}
    if um_share > UNMATCHED_MAX:
        out.update(verdict="untestable",
                   why="precincts-changed" if set(unmatched) & moved else "names",
                   unmatched=unmatched, unmatched_vote_share=round(um_share, 4))
        return out
    by_code = {code: (r, sc) for r, (code, sc) in matched.items()}
    # the ballots cast across the ground the map covers, each precinct
    # weighted by the share of its people the map holds
    board = 0.0
    for code, dd in meas["people"].items():
        people = pinfo[code]["people"]
        if people and code in by_code:
            board += ballots.get(by_code[code][0], 0) * sum(dd.values()) / people
    if board and total / board >= AT_LARGE_SHARE and len(meas["district_area"]) > 2:
        out.update(verdict="at-large", share_of_ballots=round(total / board, 3))
        return out
    forward, slight, weak = [], [], []
    for name, v in sorted(votes.items()):
        if name not in matched:
            continue
        code, sc = matched[name]
        area = meas["area"].get(code, {}).get(dkey, 0.0) / pinfo[code]["area"]
        people = pinfo[code]["people"]
        pshare = meas["people"].get(code, {}).get(dkey, 0) / people if people else 0.0
        if area < FORWARD_SHARE and pshare < FORWARD_SHARE:
            b = ballots.get(name, 0)
            row = [name, pinfo[code]["name"], v, b, round(area, 4), round(pshare, 4)]
            if v < FORWARD_VOTES or v < FORWARD_BALLOT_SHARE * max(b, 1):
                slight.append(row)
            elif sc < STRONG_MATCH:
                weak.append(row + [round(sc, 2)])
            else:
                forward.append(row)
    voted_codes = {matched[v][0] for v in votes if v in matched}
    reverse = []
    for code, dd in sorted(meas["people"].items()):
        people = pinfo[code]["people"]
        if people < REVERSE_PEOPLE or code not in by_code or code in voted_codes:
            continue
        share = dd.get(dkey, 0) / people
        name, sc = by_code[code]
        b = ballots.get(name, 0)
        if share >= REVERSE_SHARE and b >= REVERSE_BALLOTS:
            row = [name, pinfo[code]["name"], round(share, 3), b]
            if sc < STRONG_MATCH:
                weak.append(row + [round(sc, 2)])
            else:
                reverse.append(row)
    if unmatched:
        out.update(unmatched=unmatched, unmatched_vote_share=round(um_share, 4))
    if slight:
        out["slight"] = slight
    if forward or reverse:
        out["verdict"] = "fail"
        if forward:
            out["forward"] = forward
        if reverse:
            out["reverse"] = reverse
    elif weak:
        out.update(verdict="untestable", why="weak-match")
    else:
        out["verdict"] = "pass"
    if weak:
        out["weak"] = weak
    return out


def contest_status(c):
    """A contest's verdict as one district status: a failure on the 2026
    ballots is a conflict, because precinct lines can move without a rename
    and the precinct map is 2024's."""
    if c["verdict"] == "fail" and c["election"] != PRECINCT_MAP_ELECTION:
        return "conflict"
    return c["verdict"]


# The order in which one district's contests decide its status.
STATUS_ORDER = ("fail", "conflict", "pass", "at-large", "untestable", "countywide")


def district_status(contests):
    seen = {contest_status(c) for c in contests}
    for s in STATUS_ORDER:
        if s in seen:
            return s
    return "untested"


def map_verdict(status):
    n = collections.Counter(status.values())
    if n["fail"]:
        return "fails"
    if n["conflict"]:
        return "conflicts"
    if n["pass"]:
        return "passes"
    if n["at-large"]:
        return "at-large"
    if n["untestable"]:
        return "untestable"
    if n["countywide"]:
        return "voted-countywide"
    return "untested"


def precincts_moved(old, new):
    """The precincts on a later ballot whose ground has changed since the
    precinct map's own ballot, judged by name and by registered voters.

    `old` and `new` are {name: [ballots, registered]}. A name not on the old
    ballot is a new precinct. A kept name whose registered voters moved by
    more than REG_DRIFT against its county's own change has gained or lost
    ground: measured 2026-10-30 over the 1,467 precincts of the counties
    whose names did not change between November 2024 and May 2026, half
    moved by under 1.6% against their county and 95% by under 6.7%, while
    DeKalb's Valley Brook, which kept its name, went from 961 registered
    voters to 1,958 and voted in May 2026 in districts the map does not put
    it in. So a precinct can change without a rename, and registrations are
    how this check sees it.
    """
    # the county's own change, from every precinct on each ballot: a
    # county that merged precincts grows every name it kept, so a ratio over
    # the kept names alone would call each of them unchanged
    total_old = sum(v[1] for v in old.values())
    ratio = sum(v[1] for v in new.values()) / total_old if total_old else 1.0
    common = [n for n in new if old.get(n, [0, 0])[1] > 0 and new[n][1] > 0]
    moved = {}
    for n in new:
        if n not in old:
            moved[n] = "new"
        elif n in common:
            drift = (new[n][1] / old[n][1]) / ratio - 1
            if abs(drift) > REG_DRIFT:
                moved[n] = "registered voters %d -> %d" % (old[n][1], new[n][1])
    return moved


def analyze(maps, contests, pinfo, turnout):
    by_county = collections.defaultdict(list)
    for code, p in pinfo.items():
        by_county[county_key(p["county"])].append(code)
    # A later ballot is read against the precinct map through the precinct
    # map's own ballot: a precinct whose name and ground are unchanged keeps
    # its November 2024 pairing, and one that is new or has moved is left
    # unpaired, so it can neither pass nor fail a contest.
    matches, moved, unmatched_names, changed = {}, {}, {}, {}
    for (el, ckey) in sorted(turnout, key=lambda k: (k[0] != PRECINCT_MAP_ELECTION, k)):
        names = list(turnout[(el, ckey)])
        mp = {code: pinfo[code] for code in by_county[ckey]}
        if el == PRECINCT_MAP_ELECTION:
            matches[(el, ckey)] = match(names, mp)
            moved[(el, ckey)] = set()
        else:
            base = matches[(PRECINCT_MAP_ELECTION, ckey)]
            mv = precincts_moved(turnout[(PRECINCT_MAP_ELECTION, ckey)], turnout[(el, ckey)])
            matches[(el, ckey)] = {n: base[n] for n in names if n in base and n not in mv}
            moved[(el, ckey)] = set(mv)
            gone = sorted(set(turnout[(PRECINCT_MAP_ELECTION, ckey)]) - set(names))
            if mv or gone:
                changed["%s %s" % (el, ckey)] = {"changed": dict(sorted(mv.items())), "gone": gone}
        left = sorted(n for n in names if n not in matches[(el, ckey)] and n not in moved[(el, ckey)])
        if left:
            unmatched_names["%s %s" % (el, ckey)] = left
    by_body = collections.defaultdict(list)
    for m in maps:
        for body in m["bodies"]:
            by_body[(county_key(m["county"]), body)].append(m)
    rows = {}           # (file, body) -> its contests and off-map contests
    for m in maps:
        for body in m["bodies"]:
            rows[(m["file"], body)] = {"contests": [], "off_map": [], "no_district": []}
    loose = []
    for c in contests:
        cands = by_body.get((c["county"], c["body"]), [])
        cands = sorted(cands, key=lambda m: m["super"] != c["super"])
        brief = {"election": c["election"], "contest": c["name"],
                 "voted": "county-wide" if c.get("countywide") else "by district"}
        if not cands:
            if c["district"] is not None:
                loose.append(dict(brief, county=c["county"]))
            continue
        hit = None
        if c["district"] is not None:
            hit = next(((m, district_key(m, c)) for m in cands if district_key(m, c)), None)
        if hit is None:
            main = next((m for m in cands if not m["super"]), cands[0])
            if c["district"] is not None and not c.get("countywide"):
                # A district the map does not have: McDuffie's school board
                # super districts, which no file draws.
                rows[(main["file"], c["body"])]["off_map"].append(brief)
            else:
                # A chair; an at-large seat; Baker's seats, named by place;
                # Bibb's at-large posts 7 and 8 and Rabun's school board
                # posts against its map of zones, all voted county-wide.
                # Recorded, and saying nothing about the map's lines.
                rows[(main["file"], c["body"])]["no_district"].append(brief)
            continue
        m, dkey = hit
        row = dict(brief, district=dkey)
        if c.get("countywide"):
            row.update(verdict="countywide", precincts_voted=c["units"])
        else:
            k = (c["election"], c["county"])
            ballots = {n: v[0] for n, v in turnout[k].items()}
            row.update(test_contest(c, m, dkey, matches[k], pinfo, ballots, moved[k]))
        rows[(m["file"], c["body"])]["contests"].append(row)
    records = []
    for m in maps:
        for body in m["bodies"]:
            r = rows[(m["file"], body)]
            if m["super"] and not r["contests"]:
                continue    # a super-district file no contest reached says nothing
            keys = sorted(m["measure"]["district_area"], key=lambda k: (len(k), k))
            status = {k: district_status([c for c in r["contests"] if c["district"] == k])
                      for k in keys}
            year = re.findall(r"(?:19|20)\d\d", m["file"])
            records.append({
                "county": m["county"], "fips": m["fips"], "body": body,
                "category": m["category"], "title": m["title"], "url": m["url"],
                "file": m["file"], "sha256": m["sha256"], "year": year[0] if year else None,
                "super": m["super"], "verdict": map_verdict(status),
                "districts": status, "contests": r["contests"], "off_map": r["off_map"],
                "no_district": r["no_district"],
                "people_outside_map": m["measure"]["people_outside"]})
    records.sort(key=lambda r: (r["county"], r["body"], r["super"]))
    return records, loose, unmatched_names, changed


def summarize(records):
    out = {}
    for body in BODIES:
        n = collections.Counter(r["verdict"] for r in records if r["body"] == body and not r["super"])
        out[body] = dict(sorted(n.items()))
    return out


# --------------------------------------------------------------- the record

def check(path):
    """The record's verdicts follow from its own contests; no network needed."""
    with open(path, encoding="utf-8") as fh:
        rec = json.load(fh)
    problems = []
    for r in rec["maps"]:
        where = "%s %s %s" % (r["county"], r["body"], r["file"])
        for k, s in r["districts"].items():
            want = district_status([c for c in r["contests"] if c["district"] == k])
            if s != want:
                problems.append("%s district %s: %s, its contests say %s" % (where, k, s, want))
        for c in r["contests"]:
            if c["district"] not in r["districts"]:
                problems.append("%s: a contest names district %s, not on the map" % (where, c["district"]))
            if c["verdict"] == "fail" and not (c.get("forward") or c.get("reverse")):
                problems.append("%s: %s fails with no evidence" % (where, c["contest"]))
        if r["verdict"] != map_verdict(r["districts"]):
            problems.append("%s: verdict %s does not follow from its districts" % (where, r["verdict"]))
        if not re.match(r"^[0-9a-f]{64}$", r.get("sha256") or ""):
            problems.append("%s: no SHA-256" % where)
    if rec["summary"] != summarize(rec["maps"]):
        problems.append("the summary does not count the maps: %s against %s"
                        % (rec["summary"], summarize(rec["maps"])))
    if problems:
        for p in problems:
            print("FAIL: " + p)
        sys.exit(1)
    print("OK: %d maps; %s" % (len(rec["maps"]), json.dumps(rec["summary"])))


def main():
    global OFFLINE
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--cache", help="directory for everything fetched and measured")
    ap.add_argument("--offline", action="store_true", help="fetch nothing")
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--check", nargs="?", const=DEFAULT_OUT, metavar="PATH",
                    help="confirm a record's verdicts follow from its contests")
    args = ap.parse_args()
    if args.check:
        check(args.check)
        return
    if not args.cache:
        ap.error("--cache DIR is required to build the record")
    OFFLINE = args.offline
    cache = os.path.abspath(args.cache)
    page = office_page(cache)
    maps = county_maps(page)
    purl = precinct_map_url(page)
    pzip = cached(os.path.join(cache, "precincts", purl.split("?")[0].rsplit("/", 1)[1]),
                  purl, binary=True)
    pinfo, psha = measure(cache, maps, pzip)
    turnout, contests = read_results(cache)
    records, loose, unmatched, changed = analyze(maps, contests, pinfo, turnout)
    record = {
        "about": ("Each county commission and school board map the General Assembly's "
                  "map office lists, tested against the precincts that voted in each "
                  "district contest. Written by ga/scripts/check_ga_county_maps.py, which "
                  "explains the test and every verdict."),
        "checked": datetime.date.today().isoformat(),
        "sources": {
            "maps": OFFICE_PAGE,
            "precinct_map": {"url": purl, "sha256": psha, "precincts": len(pinfo)},
            "results": RESULTS_API,
            "elections": [{"id": el, "date": day, "name": label} for el, day, label in ELECTIONS],
            "people": "Census 2020 blocks, TIGERweb Tracts_Blocks/MapServer/12",
        },
        "summary": summarize(records),
        "maps": records,
        "contests_without_a_map": loose,
        "precincts_changed_since_2024": changed,
        "unmatched_precinct_names": unmatched,
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(record, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print("wrote %s: %d maps; %s" % (args.out, len(records), json.dumps(record["summary"])))


if __name__ == "__main__":
    main()
