#!/usr/bin/env python3
"""
Build the pre-simplified Minnesota voting-precinct boundary file in
data/app/ from the Secretary of State's own statewide service.

WHY THIS LAYER AND NOT A COUNTY-BY-COUNTY ONE. Minnesota publishes its
precincts ONCE, statewide, from the office that maintains them: the
Secretary of State's Elections Division, served through MnGeo's enterprise
ArcGIS host. Every other state in this fleet reached precincts county by
county, from 46 separate sources in Illinois's case. Here one service
answers for all 87 counties, so the layer ships whole, like the counties
and the two legislative chambers: fetch -> simplify -> validate -> write.

WHAT THE SERVICE ALSO CARRIES, AND WHY THIS BUILDER TAKES NONE OF IT.
Its own attributes name each precinct's county commissioner district,
judicial district, soil-and-water district, hospital district, park
district and city ward (mn/WATCH.md records the seven layers that dissolve
out of it). Those are separate questions with separate cards, and a
precinct card that printed them would be answering for bodies this app has
not registered. They are dropped here; a later builder dissolves them.

THE BLANK VALUE IS A SPACE, NOT AN EMPTY STRING. Measured 2026-10-01 on
real records: `ward`, `shortlabel`, `hospdist_n` and the rest carry " " for
a precinct the field does not apply to, so a truthiness test on the raw
value reads every township as having a ward. The four properties this file
keeps are populated on every feature, which the builder checks rather than
assumes.

AND `pctcode` IS NOT UNIQUE STATEWIDE. Two of the first three records
fetched both carry "0045" (Friendship Twp in Yellow Medicine County and
Darwin Twp in Meeker). `vtdid` is the key, and the builder refuses to write
if it ever stops being one.

LICENCE. The item's own licenseInfo (ArcGIS item
6c2c813b33144d49ba993bd86b3a58ba, read 2026-10-01) is an ACCURACY
disclaimer and states no restriction on use or redistribution: the office
"maintains this data as accurately as possible, but cannot assure 100%
accuracy", and directs anyone needing definitive precinct lines to the
jurisdiction itself. That caveat is a reader-facing fact, so it is on the
layer's card, not only here. Two routes to the same statement are closed to
this project and were not fetched: resources.gisdata.mn.gov refuses every
path in its robots.txt, and www.mngeo.state.mn.us serves a managed
challenge, which is an access control.

FIDELITY. Simplification is Douglas-Peucker rather than Visvalingam, which
is the fleet's measured finding three times over: area thresholding does
not bound how far the drawn line strays, and precinct lines follow street
grids, where a compounded run of below-threshold removals turns a staircase
into a chord across the houses. WHAT IS NOT CLAIMED: Wisconsin's two
stronger instruments — the dropped-ring classifier and the per-vertex stray
ceiling — live in that instance's tree and are not applied here, so this
build is held to the agreement protocol and the exact feature count only,
which is what every other Minnesota builder is held to. A ring this file
loses would not be reported by anything.

This is an occasional OPERATOR step, not weekly CI. Watch the service's
own Service Modified stamp (mn/WATCH.md) and re-run when the Secretary of
State republishes after a re-precincting.

Prerequisites: curl (fetch, works through an HTTPS proxy) and Node.js
(mapshaper via `npx mapshaper@<pinned>`).

Usage:
    python3 mn/scripts/build_mn_precincts.py
"""

import json
import os
import random
import subprocess
import sys
import tempfile
import urllib.parse

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLEET_SCRIPTS = os.path.join(os.path.dirname(REPO_ROOT), "scripts")
APP_DATA_DIR = os.path.join(REPO_ROOT, "data", "app")
MAPSHAPER = "mapshaper@0.6.102"  # pinned for reproducible output (fleet convention)

SERVICE = (
    "https://enterprise.gisdata.mn.gov/aghost/rest/services/"
    "us_mn_state_sos/bdry_votingdistricts/FeatureServer/0"
)
USER_AGENT = "districtry/1.0 (+https://districtry.com/mn/)"
PAGE_SIZE = 2000  # the service's own maxRecordCount, read 2026-10-01

# The state envelope the app accepts a click in (the worksheet's
# permalink_gate) — validation samples uniformly over it.
STATE_BBOX = {"minLng": -97.24, "minLat": 43.49, "maxLng": -89.48, "maxLat": 49.39}

# Kept: the unique key, the self-describing label the card leads with, and
# the two governments a reader needs to place it. Everything else the
# service carries belongs to another layer's card.
KEEP_FIELDS = ["vtdid", "pctname", "countyname", "mcdname", "ctu_type"]

OUT_FILE = "mn-precincts.json"
SIMPLIFY_INTERVAL = "4"  # metres; Douglas-Peucker, see FIDELITY above
EXPECT_FEATURES = 4105  # the service's own returnCountOnly, read 2026-10-01
VALIDATION_KEY = "vtdid"
PRECISION = "0.000001"  # 6 decimals ~= 0.11 m
SAMPLES = 6000  # more than the fleet's 2,000: 4,105 features, most of them small


def require_robots():
    """Read the host's robots.txt with the client that will crawl, before the
    first fetch. Measured 2026-10-01: this host answers 404 — no published
    policy, so allow all, and no crawl delay to honour. Asked again on every
    run rather than trusted to that measurement."""
    sys.path.insert(0, FLEET_SCRIPTS)
    import requests  # noqa: E402  (fleet scraper dependency)
    import robots_policy  # noqa: E402

    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    gate = robots_policy.RobotsGate(session, USER_AGENT)
    url = SERVICE + "/query"
    ok, why = gate.allows(url)
    print("robots: %s — %s" % ("allowed" if ok else "REFUSED", why), file=sys.stderr)
    if not ok:
        raise RuntimeError(
            "mn-precincts: the Secretary of State's host refuses this client — "
            "not fetching. %s" % why
        )
    delay = gate.crawl_delay(url)
    if delay:
        raise RuntimeError(
            "mn-precincts: this host now states Crawl-delay %s; the paged fetch "
            "below does not pace itself — add a pacer before re-running" % delay
        )


def fetch_page(offset):
    query = {
        "where": "1=1",
        "outFields": ",".join(KEEP_FIELDS),
        "returnGeometry": "true",
        "outSR": "4326",
        "geometryPrecision": "6",
        "resultOffset": str(offset),
        "resultRecordCount": str(PAGE_SIZE),
        "orderByFields": "objectid",
        "f": "geojson",
    }
    url = SERVICE + "/query?" + urllib.parse.urlencode(query)
    out = subprocess.run(
        ["curl", "-sS", "--fail", "--max-time", "600", url],
        check=True, capture_output=True,
    ).stdout
    body = json.loads(out)
    # An API error is not an empty answer: ArcGIS reports one in the body
    # with a 200, and .get("features", []) would read it as "no precincts".
    if "error" in body:
        raise RuntimeError("mn-precincts: the service returned an error: %s" % body["error"])
    return body


def fetch_all():
    features = []
    offset = 0
    while True:
        page = fetch_page(offset)
        got = page.get("features")
        if got is None:
            raise RuntimeError("mn-precincts: page at offset %d carried no features key" % offset)
        features.extend(got)
        print("  fetched %d (offset %d)" % (len(got), offset), file=sys.stderr)
        if len(got) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        if offset > 20 * PAGE_SIZE:
            raise RuntimeError("mn-precincts: paging did not terminate")
    return {"type": "FeatureCollection", "features": features}


def check_properties(features):
    """Every property this file keeps must be populated on every feature.
    The service's own blank is a single space, so a space counts as absent."""
    blank = {}
    for f in features:
        props = f.get("properties") or {}
        for key in KEEP_FIELDS:
            value = props.get(key)
            if value is None or not str(value).strip():
                blank[key] = blank.get(key, 0) + 1
    if blank:
        raise RuntimeError(
            "mn-precincts: %s — refusing to write a file whose cards would "
            "print nothing" % ", ".join("%s blank on %d features" % kv for kv in sorted(blank.items()))
        )
    keys = [(f.get("properties") or {}).get(VALIDATION_KEY) for f in features]
    if len(set(keys)) != len(keys):
        raise RuntimeError(
            "mn-precincts: %s is no longer unique (%d features, %d distinct) — it is "
            "the key this layer joins on" % (VALIDATION_KEY, len(keys), len(set(keys)))
        )


def run_mapshaper(source_path, out_path):
    subprocess.run(
        [
            "npx", "-y", MAPSHAPER, source_path,
            "-simplify", "dp", "keep-shapes", "interval=" + SIMPLIFY_INTERVAL,
            "-o", "precision=" + PRECISION, "format=geojson", out_path,
        ],
        check=True, cwd=REPO_ROOT,
    )


# --- point-in-polygon mirroring index.html's even-odd test (so validation
#     agrees with what the app computes at runtime) — fleet-standard copy ---
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
    return [
        (f["properties"].get(key_prop), f["geometry"], _bbox(f["geometry"]))
        for f in features if f.get("geometry")
    ]


def _districts_at(model, pt):
    hits = []
    for key, geom, bb in model:
        if bb[0] <= pt[0] <= bb[2] and bb[1] <= pt[1] <= bb[3] and _point_in_geometry(pt, geom):
            hits.append(key)
    return hits


def validate(source_features, result_features, key_prop, samples=SAMPLES, seed=2024):
    """Refuse the build unless simplification preserves precinct coverage over
    the state envelope vs the full-precision fetch — the fleet's uniform
    random-point protocol. A point landing in two result precincts is a
    topology break: precincts tile the state and never overlap."""
    src = _model(source_features, key_prop)
    new = _model(result_features, key_prop)
    rng = random.Random(seed)
    agree = overlaps = 0
    for _ in range(samples):
        pt = (rng.uniform(STATE_BBOX["minLng"], STATE_BBOX["maxLng"]),
              rng.uniform(STATE_BBOX["minLat"], STATE_BBOX["maxLat"]))
        s_hits = _districts_at(new, pt)
        if len(s_hits) > 1:
            overlaps += 1
        o_hits = _districts_at(src, pt)
        o = o_hits[0] if len(o_hits) == 1 else (None if not o_hits else "MULTI")
        s = s_hits[0] if len(s_hits) == 1 else (None if not s_hits else "MULTI")
        if o == s:
            agree += 1
    pct = 100.0 * agree / samples
    if overlaps > 0:
        return False, "topology broken: %d/%d points fell in >1 precinct" % (overlaps, samples)
    if pct < 99.5:
        return False, "point-in-precinct agreement only %.2f%% (need >= 99.5%%)" % pct
    return True, "%d/%d (%.2f%%) agreement over the state envelope, 0 overlaps" % (
        agree, samples, pct)


def main():
    require_robots()
    source = fetch_all()
    check_properties(source["features"])

    n_src = len(source["features"])
    if n_src != EXPECT_FEATURES:
        raise RuntimeError(
            "mn-precincts: the service returned %d features, expected %d. A "
            "re-precincting moves this number legitimately — re-read the count "
            "from the service and update EXPECT_FEATURES deliberately rather "
            "than loosening it" % (n_src, EXPECT_FEATURES)
        )

    with tempfile.TemporaryDirectory() as tmp:
        src_path = os.path.join(tmp, "precincts-src.geojson")
        with open(src_path, "w") as f:
            json.dump(source, f)
        out_tmp = os.path.join(tmp, "precincts.geojson")
        run_mapshaper(src_path, out_tmp)
        with open(out_tmp) as f:
            simplified = json.load(f)

    n = len(simplified["features"])
    if n != EXPECT_FEATURES:
        raise RuntimeError(
            "mn-precincts: %d features after simplify (expected %d) — a whole "
            "precinct was dropped, which costs a reader their answer there; "
            "refusing to write" % (n, EXPECT_FEATURES)
        )

    ok, msg = validate(source["features"], simplified["features"], VALIDATION_KEY)
    if not ok:
        raise RuntimeError("mn-precincts validation failed: %s" % msg)

    compact = json.dumps(simplified, separators=(",", ":"))
    if json.loads(compact) != simplified:
        raise RuntimeError("mn-precincts round-trip mismatch before writing")

    os.makedirs(APP_DATA_DIR, exist_ok=True)
    out_path = os.path.join(APP_DATA_DIR, OUT_FILE)
    with open(out_path, "w") as f:
        f.write(compact)

    print(
        "mn-precincts -> data/app/%s: %d features (statewide); %s; %d bytes "
        "(dp interval=%s m, 6dp)"
        % (OUT_FILE, n, msg, len(compact), SIMPLIFY_INTERVAL),
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
