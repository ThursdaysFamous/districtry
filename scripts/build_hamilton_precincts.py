#!/usr/bin/env python3
"""
Build il/data/app/hamilton-precincts.json — Hamilton County's sixteen voting
precincts, from the county's own ArcGIS Online layer.

WHY A SHIPPED FILE AND NOT THE LIVE FETCH IT REPLACES. Until 2026-10-13 the app
read Voter_Precincts_Hamilton live on every first toggle. That layer is hosted
in the county's vendor-run ArcGIS Online organisation, and the organisation has
a request quota shared by everyone who reads any of its services. Measured
2026-10-13 at 17:07 UTC, the query answered HTTP 200 with

    {"error":{"code":429,"message":"Unable to perform query. Too many requests.",
     "details":["API calls quota exceeded (6063 request units)! maximum allowed
     request units (6000) per Minute. Retry after 60 sec."]}}

so a reader's precinct card showed an error whenever somebody else had used up
the county's minute, and the CI tile check failed at random on the same point.
The layer's data was last edited 2023-12-11 (its own editingInfo), so a copy
taken here goes stale only when the county re-precincts. Shipping it puts
Hamilton in the county-precinct vector-tile archive beside the other counties
whose precincts ship, and takes the county's quota out of a reader's path.

WHAT IT READS AND WHAT IT REFUSES. The layer has seventeen rows and sixteen
precincts: OBJECTID 12 carries a null Precinct_Name and its polygon duplicates
DAHLGREN 1's exactly (recorded in il/index.html's Hamilton comment), so only
named rows are asked for. The build refuses unless exactly sixteen distinct
names come back and every one is a name the Clerk's polling notice joins on
(data/app/hamilton-precinct-polling.json, built by
build_hamilton_precinct_polling.py). Names are kept as the county writes them,
with runs of whitespace collapsed and the ends trimmed — the GIS writes
"MCLEANSBORO 4 " with a trailing space.

ESRI JSON, NOT GEOJSON. The query asks for f=json and nests the rings by
containment (group_rings, shared with build_metro_outline), for the reason the
app's arcgis-loader engine block records: ArcGIS's GeoJSON export can unnest a
feature's holes into extra shells.

A QUOTA REFUSAL IS RETRIED, NOT READ AS DATA. A 429 envelope waits the time the
server names (at most 90 s) and asks once more; any other error envelope stops
the build.

THIS IS A RARE OPERATOR STEP. Re-run only if the county re-precincts. --check
fetches and compares, so it needs the network.

Usage:
    python3 scripts/build_hamilton_precincts.py            # fetch + write
    python3 scripts/build_hamilton_precincts.py --check    # fetch + compare
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import requests  # noqa: E402
from build_metro_outline import group_rings  # noqa: E402  (shared — do not fork)
from scraper_common import (  # noqa: E402  (shared machinery -- do not fork)
    UA_HEADERS_ROSTER_BOT,
    require_robots_once,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "il", "data", "app", "hamilton-precincts.json")
POLLING_PATH = os.path.join(REPO_ROOT, "il", "data", "app", "hamilton-precinct-polling.json")

LAYER = ("https://services.arcgis.com/4YineAQdtmx0tv46/arcgis/rest/services/"
         "Voter_Precincts_Hamilton/FeatureServer/0")
NAME_FIELD = "Precinct_Name"
EXPECTED_PRECINCTS = 16
COORD_PRECISION = 6           # ~11 cm; the app's other boundary files match
REQUEST_TIMEOUT = 120
QUOTA_WAIT_CAP_S = 90


def fetch_layer():
    params = {
        "where": NAME_FIELD + " IS NOT NULL",
        "outFields": NAME_FIELD,
        "outSR": "4326",
        "geometryPrecision": str(COORD_PRECISION),
        "f": "json",
    }
    url = LAYER + "/query?" + urllib.parse.urlencode(params)
    require_robots_once(url, UA_HEADERS_ROSTER_BOT["User-Agent"],
                        headers=UA_HEADERS_ROSTER_BOT,
                        label="il-build-hamilton-precincts")
    for attempt in (1, 2):
        resp = requests.get(url, headers=UA_HEADERS_ROSTER_BOT, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        payload = resp.json()
        err = payload.get("error")
        if not err:
            return payload
        details = " ".join(err.get("details") or [])
        if err.get("code") == 429 and attempt == 1:
            m = re.search(r"retry after (\d+) ?s", details, re.I)
            wait = min(int(m.group(1)) if m else 60, QUOTA_WAIT_CAP_S)
            print("  the county's ArcGIS quota refused the query; waiting %d s "
                  "and asking once more" % wait, file=sys.stderr)
            time.sleep(wait)
            continue
        raise RuntimeError("ArcGIS error %s: %s %s"
                           % (err.get("code"), err.get("message"), details))
    raise RuntimeError("unreachable")


def round_rings(rings):
    out = []
    for ring in rings:
        pts = [[round(x, COORD_PRECISION), round(y, COORD_PRECISION)] for x, y in ring]
        if pts and pts[0] != pts[-1]:
            pts.append(list(pts[0]))
        out.append(pts)
    return out


def build():
    payload = fetch_layer()
    with open(POLLING_PATH, encoding="utf-8") as f:
        polling_names = set(json.load(f)["precincts"])

    features = []
    for row in payload.get("features") or []:
        raw = (row.get("attributes") or {}).get(NAME_FIELD)
        name = re.sub(r"\s+", " ", str(raw or "")).strip()
        if not name:
            raise RuntimeError("a row came back with no name despite the IS NOT NULL "
                               "filter — the field may have been renamed")
        rings = (row.get("geometry") or {}).get("rings") or []
        if not rings:
            raise RuntimeError("%s came back with no geometry" % name)
        groups = group_rings(round_rings(rings))
        geometry = ({"type": "Polygon", "coordinates": groups[0]} if len(groups) == 1
                    else {"type": "MultiPolygon", "coordinates": groups})
        features.append({"type": "Feature",
                         "properties": {NAME_FIELD: name},
                         "geometry": geometry})

    names = [f["properties"][NAME_FIELD] for f in features]
    if len(features) != EXPECTED_PRECINCTS:
        raise RuntimeError("expected exactly %d named precincts, got %d (%s) — if the "
                           "county re-precincted, rebuild the polling file from the "
                           "Clerk's next notice too" % (EXPECTED_PRECINCTS, len(features),
                                                        ", ".join(sorted(names))))
    if len(set(names)) != len(names):
        raise RuntimeError("duplicate precinct names %s"
                           % sorted({n for n in names if names.count(n) > 1}))
    unjoined = sorted(set(names) - polling_names)
    if unjoined:
        raise RuntimeError("%s not in the Clerk's polling notice (%s) — the card joins "
                           "on the name" % (unjoined, os.path.basename(POLLING_PATH)))

    features.sort(key=lambda f: f["properties"][NAME_FIELD])
    return {
        "type": "FeatureCollection",
        "source": LAYER,
        "sourceNote": ("Hamilton County's own precinct layer, named rows only (a "
                       "seventeenth, unnamed row duplicates DAHLGREN 1)."),
        "features": features,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true",
                        help="fetch and compare against the shipped file")
    args = parser.parse_args()
    try:
        payload = build()
    except Exception as exc:  # noqa: BLE001
        print("FATAL: %s" % exc, file=sys.stderr)
        sys.exit(1)

    text = json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n"
    if args.check:
        if not os.path.exists(OUT_PATH):
            print("FAIL: %s is missing" % OUT_PATH, file=sys.stderr)
            sys.exit(1)
        with open(OUT_PATH, encoding="utf-8") as f:
            if f.read() != text:
                print("FAIL: %s does not match a fresh read of the county's layer — "
                      "rebuild, and bump the service-worker cache (this file is "
                      "cache-first)" % OUT_PATH, file=sys.stderr)
                sys.exit(1)
        print("build-hamilton-precincts: OK — shipped file matches the county's layer "
              "(%d precincts)" % len(payload["features"]))
        return
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(text)
    print("wrote %s: %d precincts" % (OUT_PATH, len(payload["features"])), file=sys.stderr)


if __name__ == "__main__":
    main()
