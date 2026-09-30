#!/usr/bin/env python3
"""
Build data/app/library-sites.json — every public library and branch in
Wisconsin as a point FeatureCollection for the library nearest-3 card.

SOURCE: the Department of Public Instruction's own ArcGIS Online org
(Wisconsin_DPI, services8.arcgis.com/o4NJgD3NfeHnWy06):

  WI_Public_Libraries_and_Branches/FeatureServer/6   482 outlets (measured
  2026-08-26) — main libraries and branches both, each with its own address
  and phone, which is exactly what a nearest-3 card wants. This is STATEWIDE
  where the reference instance's library card is city-scoped; DPI's licence
  (a reference-use disclaimer, shipped on the sources page) rides with it.

THE TRAP THIS BUILDER EXISTS TO RECORD: the layer carries LAT and LONG
attributes whose VALUES ARE WEB MERCATOR METERS (Abbotsford's row reads
LAT 5613250.3, LONG -10054370.3 — measured 2026-08-26). The names lie about
the units, so those attributes are never read here; geometry comes from the
query's own outSR=4326 geometry, and the state-bbox gate below is what fails
loudly if the service ever stops honoring outSR. The sibling school layers
carry honest degree attributes under four different names — in this org,
coordinate attributes are per-layer trivia, and the requested geometry is
the only coordinate contract worth holding.

An OPERATOR rebuild (DPI refreshes the directory from the annual public
library system data), not a weekly one — WATCH.md carries the row.
"""

import json
import os
import sys
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                                "scripts"))
from scraper_common import require_robots_once, UA_STDLIB_DEFAULT  # noqa: E402  (FLEET_SHARED)


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
OUT_PATH = os.path.join(REPO_ROOT, "data", "app", "library-sites.json")

LAYER = ("https://services8.arcgis.com/o4NJgD3NfeHnWy06/arcgis/rest/services"
         "/WI_Public_Libraries_and_Branches/FeatureServer/6")
OUT_FIELDS = "LIBRARY,FULL_ADDR,PHONE"
PAGE_SIZE = 2000
MIN_OUTLETS = 460   # 482 measured; a drop below this is a shrunken layer
MIN_PHONES = 440    # phones ship on nearly every outlet today

BBOX = {"min_lat": 42.4, "max_lat": 47.4, "min_lng": -93.0, "max_lng": -86.2}


def fetch_json(url):
    require_robots_once(url, UA_STDLIB_DEFAULT, label="wi-build-wi-libraries")
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def clean_addr(addr):
    """FULL_ADDR prints a double space between street and city — read the
    gap as the comma it is (same shape as the school layers)."""
    if not addr:
        return None
    parts = [p for p in str(addr).split("  ") if p.strip()]
    return ", ".join(" ".join(p.split()) for p in parts)


def main():
    expected = int(fetch_json(
        LAYER + "/query?where=1%3D1&returnCountOnly=true&f=json")["count"])
    feats = []
    offset = 0
    while True:
        d = fetch_json(LAYER + "/query?where=1%3D1&outFields=" + OUT_FIELDS +
                       "&outSR=4326&f=json&resultOffset=%d&resultRecordCount=%d"
                       % (offset, PAGE_SIZE))
        if "error" in d:
            raise SystemExit("the layer answered an error: %s" % d["error"])
        page = d.get("features", [])
        feats.extend(page)
        if len(page) < PAGE_SIZE and not d.get("exceededTransferLimit"):
            break
        offset += len(page)
    if len(feats) != expected:
        raise SystemExit("paged %d outlets against the layer's own count of %d"
                         % (len(feats), expected))
    if expected < MIN_OUTLETS:
        raise SystemExit("layer carries %d outlets, floor %d — read the change "
                         "before moving the floor" % (expected, MIN_OUTLETS))

    features = []
    phones = 0
    for f in feats:
        attrs = f.get("attributes") or {}
        geom = f.get("geometry") or {}
        name = (attrs.get("LIBRARY") or "").strip()
        if not name:
            raise SystemExit("an outlet came back with no LIBRARY name (attrs=%r)" % attrs)
        lng, lat = geom.get("x"), geom.get("y")
        if lng is None or lat is None:
            raise SystemExit("%r came back with no geometry" % name)
        if not (BBOX["min_lat"] <= lat <= BBOX["max_lat"] and
                BBOX["min_lng"] <= lng <= BBOX["max_lng"]):
            raise SystemExit("%r sits at (%s, %s) — outside Wisconsin; outSR was "
                             "ignored (the LAT/LONG attributes are mercator meters "
                             "and are never the answer)" % (name, lat, lng))
        phone = (attrs.get("PHONE") or "").strip() or None
        if phone:
            phones += 1
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point",
                         "coordinates": [round(lng, 6), round(lat, 6)]},
            "properties": {
                "name": name,
                "address": clean_addr(attrs.get("FULL_ADDR")),
                "phone": phone,
            },
        })
    if phones < MIN_PHONES:
        raise SystemExit("only %d of %d outlets carry a phone (floor %d) — "
                         "the PHONE column moved" % (phones, len(features), MIN_PHONES))
    no_addr = sum(1 for f in features if not f["properties"]["address"])
    if no_addr:
        raise SystemExit("%d outlets carry no address — FULL_ADDR moved" % no_addr)

    features.sort(key=lambda f: f["properties"]["name"].lower())
    with open(OUT_PATH, "w") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f,
                  ensure_ascii=False, separators=(",", ":"))
    print("wrote %d library outlets (%d with phones) -> %s"
          % (len(features), phones, os.path.relpath(OUT_PATH, REPO_ROOT)))


if __name__ == "__main__":
    sys.exit(main())
