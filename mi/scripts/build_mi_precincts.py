#!/usr/bin/env python3
"""
Build data/app/mi-precincts.json — all 3,895 of Michigan's 2026-cycle voting
precincts, as a polygon FeatureCollection for the precinct card.

SOURCE: the Michigan Bureau of Elections' own "2026 Voting Precincts"
(AGO item c349bc2bb6c2468594d341a09f520ea8), service
`services3.arcgis.com/dxRQUfTDNtfqZ301/.../2026_Voting_Precincts`. Licence
stated outright on the item, the same wording the commissioner flagship
relies on: "this dataset is a public record and ... there are no restrictions
on the use, reproduction, or distribution of this dataset".

THIS BUILDER NEARLY SHIPPED THE 2024 MAP, AND HOW IT ALMOST DID IS THE
REUSABLE PART. The state's `OpenData/boundaries` MapServer — the one carrying
the commissioner flagship at layer 10 — publishes a precinct layer per cycle:
2014, 2016, 2018, 2020, 2022 and, at layer 9, 2024. Enumerating that
MapServer's layers shows 2024 as the newest, and a first draft of this script
built from it, gates and all: 4,340 precincts, 100.00% agreement, every check
green. **A COMPLETE ANSWER FROM AN INCOMPLETE PLACE TO LOOK.** The 2026 map is
not on that MapServer at all — it lives on the state's ArcGIS Online ORG, on a
different host, and Michigan consolidated precincts between the cycles, so the
2024 layer is not merely older but 445 precincts wrong (4,340 -> 3,895).

That is CLAUDE.md's own Douglas/Vermilion rule for a second time, in a state
rather than a county: A SERVICE SHOWS WHAT IT PUBLISHES; THE ORG SHOWS WHAT
THE PUBLISHER HAS. The org query that finds it costs one request —
`arcgis.com/sharing/rest/search?q=owner:michigan_admin AND precinct` — and it
should be run BEFORE reading any MapServer's layer list, not after. What
caught it here was not that query but this repo's own guidebook, whose
Michigan precinct cell already read "the state publishes a current 2026
Voting Precincts layer (measured, same org as the flagship)". THE RECORD WAS
RIGHT AND THE BUILD WAS WRONG.

FOUR ITEMS SERVE THE 2026 MAP AND THIS PINS THE DOCUMENTED ONE. The state's
own current Election District Viewer v2 wires `VotingPrecincts2026_051926_gdb`
— a dated file-geodatabase upload with an empty description, no snippet, and
TRUNCATED field names (`PrecinctLo`, `Jurisdicti`, `Registered`: the 10-char
shapefile limit). The curated `2026 Voting Precincts` item carries the title,
the snippet, the licence, the description quoted below, and the FULL field
names the 2024 layer used. Both report 3,895 `Precincts_2026_FINAL` features.
This builds from the curated item and GATES ON THE OTHER AGREEING: if the two
ever report different counts, one of them has moved and the build stops rather
than silently preferring either.

THE STATE'S OWN CAVEAT SHIPS ON THE CARD, from the item description: "The 2026
Precinct data set represents the geography used for the 2026 election cycle.
Information was collected from local election officials along with
county/local GIS authorities as well as a validation done by most, but not all
jurisdictions. BOE maintains every effort to keep this data correct, however
the data set is only as good as the information received from the local
election official." A precinct card implying more certainty than its own
publisher claims would break this project's honesty rule by omission.

POLLING PLACES ARE NOT IN THIS LAYER AT ALL, which is the strongest form of
the fleet's polling-data discipline (ia/scripts/build_ia_precincts.py has to
DECLINE fields that exist; here there are none to decline). What the layer
DOES carry and this builder deliberately drops is `Tabulator_Voter_Assist` —
the voting equipment model. It changes on a different clock from the boundary,
it is not what a precinct card claims to answer, and a field that was never
fetched cannot be added by a later edit that forgets why.

WHAT SHIPS, and why each field earns its place:
  * `name`     — Precinct_Long_Name ("Alcona Township, Precinct 1")
  * `county`   — joined from the shipped state-counties.json by COUNTYFIPS,
                 because the layer carries the FIPS and no county NAME
  * `geoid`    — the county-subdivision GEOID, "26" + COUNTYFIPS + MCDFIPS
  * `voters`   — Registered_Voters, labelled with its cycle on the card

THREE MEASUREMENTS THIS BUILDER GATES ON (all 2026-09-04, on the 2026 layer):

1. PRECINCTID IS A REAL UNIQUE KEY — 3,895 distinct values over 3,895 rows.
   That is what makes the agreement gate below meaningful; a repeated key
   would make "the same precinct" unprovable at a sampled point.

2. THE MCD JOIN IS EXACT: every one of the 1,530 distinct
   "26"+COUNTYFIPS+MCDFIPS keys resolves to a county-subdivision GEOID in
   TIGERweb's own MCD fabric — the layer this instance shipped one PR
   earlier — so the precinct card can name its township or city on a verified
   key rather than a fuzzy name match. Note the count is 1,530 on BOTH the
   2024 and 2026 maps: Michigan consolidated precincts WITHIN its
   municipalities and did not change how many municipalities there are.

3. THE REGISTERED-VOTER TOTAL IS A SANITY CHECK WITH A REAL COMPARAND:
   8,292,351 across the 3,895 precincts, against Michigan's ~8.3 M registered
   voters. A build whose total left the band would mean the fetch lost records
   or the field changed meaning. The band is deliberately wide (7.5-9.5 M):
   this is a did-the-fetch-work check, not a claim about turnout.

EVERY ROW ON THE 2026 MAP HAS A NAME. The 2024 map had exactly one that did
not (Milan precinct 01W, in Washtenaw — Milan straddles the Washtenaw/Monroe
line, which the "W" marks), and the compose-from-jurisdiction fallback written
for it is KEPT rather than deleted: it costs nothing, it guards the next
cycle, and it prints when it fires so an unexercised guard cannot go quietly
wrong. The builder still fails if a row lacks even a jurisdiction and number.

PAGINATION IS REQUIRED: maxRecordCount is 2,000, below 3,895.

SIMPLIFICATION IS REQUIRED and is the same topology-aware mapshaper pipeline
the fleet's other precinct and district builders use (Visvalingam,
keep-shapes), with the same 2,000-uniform-random-point agreement gate: >= 99.5%
agreement against the full-precision fetch and ZERO points landing in two
precincts. Michigan's precincts follow municipal and road lines rather than
county lines, so they are small and densely vertexed — the retain fraction is
conservative for that reason, exactly as Iowa's is.
"""

import json
import os
import random
import subprocess
import sys
import tempfile
import time
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                                "scripts"))
from scraper_common import require_robots_once, UA_STDLIB_DEFAULT  # noqa: E402  (FLEET_SHARED)


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
APP_DATA_DIR = os.path.join(REPO_ROOT, "data", "app")
OUT_PATH = os.path.join(APP_DATA_DIR, "mi-precincts.json")
COUNTIES_PATH = os.path.join(APP_DATA_DIR, "state-counties.json")

# The CURATED item (title, snippet, licence, description, full field names).
LAYER_URL = ("https://services3.arcgis.com/dxRQUfTDNtfqZ301/arcgis/rest/"
             "services/2026_Voting_Precincts/FeatureServer/0")
# The SECOND WITNESS: the dated gdb upload the state's own Election District
# Viewer v2 wires. Same 3,895 Precincts_2026_FINAL features, truncated field
# names, empty description. Only its COUNT is read — if the two ever disagree,
# one has moved and this build stops rather than silently preferring either.
WITNESS_URL = ("https://services3.arcgis.com/dxRQUfTDNtfqZ301/arcgis/rest/"
               "services/VotingPrecincts2026_051926_gdb/FeatureServer/0")
# Deliberately excludes Tabulator_Voter_Assist — see the module docstring.
# Never add it here without a display contract that dates it.
OUT_FIELDS = ("PRECINCTID,COUNTYFIPS,MCDFIPS,PRECINCT,Precinct_Long_Name,"
              "Jurisdiction_Name,Registered_Voters")
PAGE_SIZE = 2000  # the layer's own maxRecordCount

EXPECT_FEATURES = 3895
EXPECT_COUNTIES = 83
EXPECT_MCD_KEYS = 1530
ELECTION_CYCLE = 2026

# A did-the-fetch-work band, not a turnout claim (docstring measurement 3).
VOTERS_MIN, VOTERS_MAX = 7_500_000, 9_500_000

# Michigan's own envelope (the worksheet's metro_bbox), used as the sample
# region for the agreement gate. Water-inclusive, like the county fabric.
STATE_BBOX = {"minLng": -90.42, "minLat": 41.69, "maxLng": -82.12, "maxLat": 48.31}

MAPSHAPER = "mapshaper@0.6.102"  # pinned for reproducible output (fleet convention)
SIMPLIFY_RETAIN = "20%"  # small, densely-vertexed polygons — the Iowa-precinct setting
PRECISION = "0.000001"  # 6 decimals ~= 0.11 m


def fetch_json(url, attempts=4):
    """Retry with backoff. MEASURED, NOT SPECULATIVE: gisagocss.state.mi.us
    reset a connection mid-paging on 2026-09-04 (errno 104) between two runs
    that each fetched all 4,340 records cleanly. This build makes five paged
    requests plus a count, so a single transient reset would otherwise throw
    away a full simplify-and-validate cycle. A reset is not a reason to ship
    a partial file — every failure still raises once the attempts are spent."""
    require_robots_once(url, UA_STDLIB_DEFAULT, label="mi-build-mi-precincts")
    last = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=180) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as exc:  # URLError, socket timeout, malformed JSON
            last = exc
            if attempt == attempts - 1:
                break
            time.sleep(2 ** attempt)
    raise SystemExit("%s failed after %d attempts: %s" % (url, attempts, last))


def layer_count(url=None):
    d = fetch_json((url or LAYER_URL) + "/query?where=1%3D1&returnCountOnly=true&f=json")
    return int(d["count"])


def fetch_all_geojson():
    """Page past the 1,000-record cap, requesting GeoJSON directly with
    6-decimal precision so the raw payload is trimmed before mapshaper."""
    feats = []
    offset = 0
    while True:
        url = (LAYER_URL + "/query?where=1%3D1&outFields=" + OUT_FIELDS +
               "&outSR=4326&geometryPrecision=6&f=geojson"
               "&resultOffset=%d&resultRecordCount=%d" % (offset, PAGE_SIZE))
        d = fetch_json(url)
        if "error" in d:
            raise SystemExit("%s answered an error: %s" % (LAYER_URL, d["error"]))
        page = d.get("features", [])
        feats.extend(page)
        if len(page) < PAGE_SIZE and not d.get("properties", {}).get("exceededTransferLimit"):
            return feats
        offset += len(page)


def county_names():
    """FIPS -> county name, from the file this instance already ships. The
    precinct layer carries COUNTYFIPS and no county NAME, and inventing one
    from a lookup table would be a second source to keep in step."""
    with open(COUNTIES_PATH) as f:
        counties = json.load(f)
    out = {}
    for feat in counties["features"]:
        props = feat["properties"]
        out[props["COUNTY"]] = props["NAME"]
    if len(out) != EXPECT_COUNTIES:
        raise SystemExit("state-counties.json keys %d counties, expected %d"
                         % (len(out), EXPECT_COUNTIES))
    return out


def run_mapshaper(source_path, out_path):
    subprocess.run(
        [
            "npx", "-y", MAPSHAPER, source_path,
            "-simplify", "visvalingam", "keep-shapes", SIMPLIFY_RETAIN,
            "-o", "precision=" + PRECISION, "format=geojson", out_path,
        ],
        check=True, cwd=REPO_ROOT,
    )


# --- point-in-polygon mirroring index.html's even-odd test (fleet-standard copy) ---
def _point_in_ring(pt, ring):
    x, y = pt
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _point_in_geometry(pt, geom):
    if geom["type"] == "Polygon":
        inside = False
        for ring in geom["coordinates"]:
            if _point_in_ring(pt, ring):
                inside = not inside
        return inside
    if geom["type"] == "MultiPolygon":
        for poly in geom["coordinates"]:
            inside = False
            for ring in poly:
                if _point_in_ring(pt, ring):
                    inside = not inside
            if inside:
                return True
    return False


def _bbox(geom):
    b = [1e9, 1e9, -1e9, -1e9]

    def walk(c):
        if c and isinstance(c[0], (int, float)):
            b[0], b[1] = min(b[0], c[0]), min(b[1], c[1])
            b[2], b[3] = max(b[2], c[0]), max(b[3], c[1])
        else:
            for x in c:
                walk(x)

    walk(geom["coordinates"])
    return b


def _model(features, key_prop):
    return [(f["properties"].get(key_prop), f["geometry"], _bbox(f["geometry"]))
            for f in features]


def _precincts_at(model, pt):
    hits = []
    for key, geom, bb in model:
        if bb[0] <= pt[0] <= bb[2] and bb[1] <= pt[1] <= bb[3] and _point_in_geometry(pt, geom):
            hits.append(key)
    return hits


# The state's own 2026 fabric overlaps itself in two measured places, so an
# overlap is only a defect when SIMPLIFICATION caused it. Measured 2026-09-04
# at 2 of 2,000 uniform points, both present in the FULL-PRECISION fetch:
#
#   * City of Allegan, Precinct 1  x  Allegan Township, Precinct 1
#     (annexation lag — the township polygon still carries land the city took)
#   * Kalkaska Township, Precinct 1  x  Kalkaska Township, Precinct 2
#     (two precincts of one township overlapping each other)
#
# Iowa's precinct builder records the same class of thing (78 source
# self-intersections mapshaper cannot repair) and does not treat it as fatal,
# because the point-agreement gate is what actually proves correctness. The
# ceiling below is a real gate, not a formality: a source that degrades past
# it stops the build.
MAX_INHERITED_OVERLAP = 5  # of 2,000 sampled points; 2 measured 2026-09-04


def validate(source_features, result_features, key_prop, samples=2000, seed=2024):
    """Refuse the build unless simplification preserves precinct coverage over
    the state envelope vs. the full-precision fetch — the project's 2,000
    uniform-random-point protocol.

    AN OVERLAP IS JUDGED AGAINST THE SOURCE, NOT IN ISOLATION. A point landing
    in two SIMPLIFIED precincts where the full-precision source also puts it in
    two is INHERITED: the state drew it that way and simplification is
    blameless. A point landing in two simplified precincts where the source
    puts it in one is INTRODUCED, and is fatal — that is a topology break this
    build caused. The first draft of this function counted both together and
    refused a correct build."""
    src = _model(source_features, key_prop)
    new = _model(result_features, key_prop)
    rng = random.Random(seed)
    agree = introduced = inherited = 0
    witnesses = []
    for _ in range(samples):
        pt = (rng.uniform(STATE_BBOX["minLng"], STATE_BBOX["maxLng"]),
              rng.uniform(STATE_BBOX["minLat"], STATE_BBOX["maxLat"]))
        s_hits = _precincts_at(new, pt)
        o_hits = _precincts_at(src, pt)
        if len(s_hits) > 1:
            if len(o_hits) > 1:
                inherited += 1
                if len(witnesses) < 4:
                    witnesses.append("%.5f,%.5f %s" % (pt[0], pt[1], sorted(s_hits)))
            else:
                introduced += 1
        o = o_hits[0] if len(o_hits) == 1 else (None if not o_hits else "MULTI")
        s = s_hits[0] if len(s_hits) == 1 else (None if not s_hits else "MULTI")
        if o == s:
            agree += 1
    pct = 100.0 * agree / samples
    if introduced > 0:
        return False, ("simplification broke topology: %d/%d points fell in >1 "
                       "precinct where the full-precision source puts them in "
                       "one" % (introduced, samples))
    if inherited > MAX_INHERITED_OVERLAP:
        return False, ("the source overlaps itself at %d/%d sampled points "
                       "(ceiling %d) — that is a change in the state's own "
                       "fabric, not this build's doing, and is worth looking "
                       "at before shipping: %s"
                       % (inherited, samples, MAX_INHERITED_OVERLAP,
                          "; ".join(witnesses)))
    if pct < 99.5:
        return False, "point-in-precinct agreement only %.2f%% (need >= 99.5%%)" % pct
    return True, ("%d/%d (%.2f%%) agreement over the state envelope, 0 overlaps "
                  "introduced by simplification, %d inherited from the source%s"
                  % (agree, samples, pct, inherited,
                     (" (" + "; ".join(witnesses) + ")") if witnesses else ""))


def main():
    check_only = "--check" in sys.argv[1:]
    names = county_names()

    expected = layer_count()
    if expected != EXPECT_FEATURES:
        raise SystemExit(
            "'2026 Voting Precincts' now reports %d features, expected %d. A "
            "count change on a CYCLE-SCOPED layer is real information, not "
            "drift — Michigan went 4,340 -> 3,895 between the 2024 and 2026 "
            "maps. Re-verify before shipping, and run the org query first "
            "(arcgis.com/sharing/rest/search?q=owner:michigan_admin AND "
            "precinct) in case a NEWER cycle has been published somewhere "
            "this URL cannot see — that is exactly how this builder nearly "
            "shipped the 2024 map (mi/WATCH.md)"
            % (expected, EXPECT_FEATURES))
    witness = layer_count(WITNESS_URL)
    if witness != expected:
        raise SystemExit(
            "the two 2026 services disagree: the curated item reports %d "
            "features and the upload the state's own viewer wires reports %d. "
            "One has moved; resolve which before shipping either"
            % (expected, witness))
    raw = fetch_all_geojson()
    if len(raw) != expected:
        raise SystemExit("paged %d features against the layer's own count of "
                         "%d — the page cap or a filter ate records"
                         % (len(raw), expected))

    source_features = []
    counties, mcd_keys, keys = set(), set(), set()
    voters_total = 0
    composed = []
    for f in raw:
        props = f.get("properties") or {}
        geom = f.get("geometry")
        pid = (props.get("PRECINCTID") or "").strip()
        co_fips = (props.get("COUNTYFIPS") or "").strip()
        mcd_fips = (props.get("MCDFIPS") or "").strip()
        if not (pid and co_fips and mcd_fips):
            raise SystemExit("a record is missing PRECINCTID/COUNTYFIPS/MCDFIPS "
                             "(properties=%r)" % props)
        if pid in keys:
            raise SystemExit("PRECINCTID %r repeats — it is this build's join "
                             "key and the agreement gate is meaningless "
                             "without uniqueness" % pid)
        keys.add(pid)

        name = (props.get("Precinct_Long_Name") or "").strip()
        if not name:
            # UNEXERCISED ON THE 2026 MAP (every row has a name) and kept
            # anyway: the 2024 map had exactly one such row, Milan 01W in
            # Washtenaw, and the next cycle may have another. It prints when
            # it fires, so an unexercised guard cannot go quietly wrong.
            juris = (props.get("Jurisdiction_Name") or "").strip()
            number = (props.get("PRECINCT") or "").strip()
            if not (juris and number):
                raise SystemExit("%s has no name and cannot compose one "
                                 "(properties=%r)" % (pid, props))
            name = "%s, Precinct %s" % (juris, number)
            composed.append((pid, name))

        county = names.get(co_fips)
        if not county:
            raise SystemExit("%s carries COUNTYFIPS %r, which is not one of "
                             "Michigan's 83 in state-counties.json"
                             % (pid, co_fips))
        if not geom:
            raise SystemExit("%r (%s) carries no geometry" % (name, county))

        counties.add(co_fips)
        mcd_keys.add("26" + co_fips + mcd_fips)
        voters_total += int(props.get("Registered_Voters") or 0)
        source_features.append({
            "type": "Feature",
            "geometry": geom,
            "properties": {
                "pctid": pid,
                "name": name,
                "county": county,
                "geoid": "26" + co_fips + mcd_fips,
                "voters": int(props.get("Registered_Voters") or 0) or None,
            },
        })

    if len(counties) != EXPECT_COUNTIES:
        raise SystemExit("precincts span %d counties, expected %d — a county "
                         "with zero precincts would explain this"
                         % (len(counties), EXPECT_COUNTIES))
    # The MCD join (docstring measurement 2). Checked OFFLINE for its SHAPE —
    # a 10-character "26"+county+MCD key — because a build must not need a
    # third-party host up to prove its own arithmetic. The 1,530/1,530
    # resolution against TIGERweb's own MCD fabric is the recorded live
    # measurement; this gate catches the key going malformed or the distinct
    # count moving, either of which breaks the precinct card's township join.
    bad = sorted(k for k in mcd_keys if len(k) != 10 or not k.isdigit())
    if bad:
        raise SystemExit("%d MCD join keys are malformed (e.g. %r) — the "
                         "precinct card joins its township on this"
                         % (len(bad), bad[:3]))
    if len(mcd_keys) != EXPECT_MCD_KEYS:
        raise SystemExit(
            "precincts span %d distinct county-subdivision keys, expected %d. "
            "Michigan's MCD fabric moves when a city annexes or incorporates, "
            "so this is real information — re-run the join against TIGERweb's "
            "Places_CouSub layer 1 before changing the constant"
            % (len(mcd_keys), EXPECT_MCD_KEYS))
    if not (VOTERS_MIN <= voters_total <= VOTERS_MAX):
        raise SystemExit("registered voters total %d is outside the %d-%d "
                         "sanity band — the fetch lost records or the field "
                         "changed meaning" % (voters_total, VOTERS_MIN, VOTERS_MAX))

    for pid, name in composed:
        print("build-mi-precincts: composed a name for %s -> %r "
              "(the source carries none)" % (pid, name))

    if check_only:
        print("build-mi-precincts: OK (--check) — %d precincts, %d counties, "
              "%d subdivision keys, %s registered voters; source unchanged"
              % (len(source_features), len(counties), len(mcd_keys),
                 format(voters_total, ",")))
        return

    with tempfile.TemporaryDirectory() as tmp:
        src_path = os.path.join(tmp, "mi-precincts-src.geojson")
        with open(src_path, "w") as f:
            json.dump({"type": "FeatureCollection", "features": source_features}, f)
        out_tmp = os.path.join(tmp, "mi-precincts.geojson")
        run_mapshaper(src_path, out_tmp)
        with open(out_tmp) as f:
            simplified = json.load(f)

    n = len(simplified["features"])
    if n != EXPECT_FEATURES:
        raise SystemExit("%d features after simplify (expected exactly %d "
                         "precincts) — refusing to write" % (n, EXPECT_FEATURES))

    ok, msg = validate(source_features, simplified["features"], "pctid")
    if not ok:
        raise SystemExit("validation failed: %s" % msg)

    # pctid was carried through only as the validation join key — the card
    # never needs it, so it does not ship.
    for feat in simplified["features"]:
        feat["properties"].pop("pctid", None)
    simplified["features"].sort(key=lambda f: (f["properties"]["county"],
                                               f["properties"]["name"]))

    with open(OUT_PATH, "w") as f:
        json.dump(simplified, f, separators=(",", ":"))
    size = os.path.getsize(OUT_PATH)
    print("build-mi-precincts: wrote %s — %d precincts across %d counties, "
          "%s registered voters (%d cycle), %.1f KB; %s"
          % (os.path.relpath(OUT_PATH, REPO_ROOT), n, len(counties),
             format(voters_total, ","), ELECTION_CYCLE, size / 1024.0, msg))


if __name__ == "__main__":
    main()
