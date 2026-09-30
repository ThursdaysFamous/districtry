#!/usr/bin/env python3
"""
Build data/app/school-sites.json — every school site in Wisconsin, public and
private, as a point FeatureCollection for the school-site nearest-3 card.

SOURCE: the Department of Public Instruction's own ArcGIS Online org
(Wisconsin_DPI, services8.arcgis.com/o4NJgD3NfeHnWy06), two hosted layers:

  Wisconsin_Public_Schools/FeatureServer/20   2,290 sites (measured 2026-08-26)
  WI_Private_Schools/FeatureServer/2            828 sites (measured 2026-08-26)

Both are shared public. DPI's licence is a reference-use disclaimer, not a
redistribution ban — its text ships on the sources page with the layer, and it
is why the card presents proximity and never an enrollment or attendance
claim.

THREE MEASURED TRAPS, each encoded below:

  1. The public layer exceeds the service's 2,000-record page cap, so a
     single query silently returns 2,000 of 2,290. Every fetch here pages by
     resultOffset and then asserts the total against the layer's own
     returnCountOnly answer — a silent cap can never ship as a short file.
  2. The two layers RENAME their coordinate attributes (public: LAT/LON;
     private: LATITUDE/LONGITUDE) and their type field (SCHOOLTYPE vs
     SCHOOL_TYPE). The field lists are per-layer, never shared.
  3. The layers' native geometry is projected (Wisconsin Transverse Mercator,
     x≈700421 for a Racine school), so geometry must be requested with
     outSR=4326 — and because the sibling libraries layer proves this org
     can carry attribute names that lie about units, every emitted point is
     gated against the layer's own lat/lng attributes (<= ~110 m apart) and
     against the state's bounding box.

VIRTUAL PROGRAMS ARE PLACELESS AND ARE SKIPPED, BY THE SOURCE'S OWN SHAPE:
152 of the public layer's 2,290 records carry NO geometry and NO address
(measured 2026-08-26) — statewide online programs, one row per member
district ("Between the Lakes Virtual Academy" fifteen times over). A
nearest-3 card lists places, so those rows don't ship. The skip is keyed on
the record shape, never on the VIRTUAL flag, because that flag is measured
inconsistent (16 of the 152 say VIRTUAL: No — "Rural Virtual Academy" among
them); and a no-geometry record that DOES carry an address fails the build
outright, because that would be a mappable school silently dropped. Virtual
schools WITH a campus (60 of them) ship like any other.

The file is an OPERATOR rebuild, not a weekly one: DPI rotates the directory
around each school year, and WATCH.md carries the row. Rerun, read the diff,
ship it as a PR.
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
OUT_PATH = os.path.join(REPO_ROOT, "data", "app", "school-sites.json")

DPI_BASE = "https://services8.arcgis.com/o4NJgD3NfeHnWy06/arcgis/rest/services"
PAGE_SIZE = 2000

# (url, kind label, outFields, lat attr, lng attr, min SHIPPED features —
#  i.e. after the placeless-program skip, which today drops 152 public rows)
LAYERS = [
    (DPI_BASE + "/Wisconsin_Public_Schools/FeatureServer/20", "Public",
     "SCHOOL,GRADE_RANGE,FULL_ADDR,LAT,LON", "LAT", "LON", 2050),
    (DPI_BASE + "/WI_Private_Schools/FeatureServer/2", "Private",
     "SCHOOL,GRADE_RANGE,FULL_ADDR,LATITUDE,LONGITUDE", "LATITUDE", "LONGITUDE", 780),
]

# Wisconsin's extent with a small margin; a coordinate outside it means the
# service ignored outSR (projected meters would land wildly outside) or a
# record is misplaced.
BBOX = {"min_lat": 42.4, "max_lat": 47.4, "min_lng": -93.0, "max_lng": -86.2}


def fetch_json(url):
    require_robots_once(url, UA_STDLIB_DEFAULT, label="wi-build-wi-school-sites")
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def layer_count(layer_url):
    d = fetch_json(layer_url + "/query?where=1%3D1&returnCountOnly=true&f=json")
    return int(d["count"])


def fetch_all(layer_url, out_fields):
    """Page past the 2,000-record cap; the caller asserts the total."""
    feats = []
    offset = 0
    while True:
        url = (layer_url + "/query?where=1%3D1&outFields=" + out_fields +
               "&outSR=4326&f=json&resultOffset=%d&resultRecordCount=%d"
               % (offset, PAGE_SIZE))
        d = fetch_json(url)
        if "error" in d:
            raise SystemExit("%s answered an error: %s" % (layer_url, d["error"]))
        page = d.get("features", [])
        feats.extend(page)
        if len(page) < PAGE_SIZE and not d.get("exceededTransferLimit"):
            return feats
        offset += len(page)


def clean_addr(addr):
    """DPI prints FULL_ADDR with a double space between street and city
    ("1220 Mound Ave  Racine, WI 53404") — read the gap as the comma it is."""
    if not addr:
        return None
    parts = [p for p in str(addr).split("  ") if p.strip()]
    return ", ".join(" ".join(p.split()) for p in parts)


def main():
    features = []
    counts = {}
    for layer_url, kind, out_fields, lat_key, lng_key, floor in LAYERS:
        expected = layer_count(layer_url)
        raw = fetch_all(layer_url, out_fields)
        if len(raw) != expected:
            raise SystemExit("%s paged %d features against its own count of %d — "
                             "the page cap or a filter ate records"
                             % (layer_url, len(raw), expected))
        shipped = skipped = 0
        for f in raw:
            attrs = f.get("attributes") or {}
            geom = f.get("geometry") or {}
            name = (attrs.get("SCHOOL") or "").strip()
            if not name:
                raise SystemExit("%s serves a site with no SCHOOL name (attrs=%r)"
                                 % (layer_url, attrs))
            lng, lat = geom.get("x"), geom.get("y")
            if lng is None or lat is None:
                # the placeless-program shape: no geometry AND no address
                if (attrs.get("FULL_ADDR") or "").strip():
                    raise SystemExit("%r has an address but no geometry — a "
                                     "mappable school this builder refuses to "
                                     "silently drop" % name)
                skipped += 1
                continue
            if not (BBOX["min_lat"] <= lat <= BBOX["max_lat"] and
                    BBOX["min_lng"] <= lng <= BBOX["max_lng"]):
                raise SystemExit("%r sits at (%s, %s) — outside Wisconsin; outSR "
                                 "was ignored or the record is misplaced" % (name, lat, lng))
            # the layer's own coordinate attributes as the second witness
            a_lat, a_lng = attrs.get(lat_key), attrs.get(lng_key)
            if a_lat is not None and a_lng is not None:
                if abs(a_lat - lat) > 0.001 or abs(a_lng - lng) > 0.001:
                    raise SystemExit("%r: geometry (%.5f,%.5f) disagrees with its own "
                                     "%s/%s attributes (%.5f,%.5f)"
                                     % (name, lat, lng, lat_key, lng_key, a_lat, a_lng))
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point",
                             "coordinates": [round(lng, 6), round(lat, 6)]},
                "properties": {
                    "name": name,
                    "kind": kind,
                    "grades": (attrs.get("GRADE_RANGE") or "").strip() or None,
                    "address": clean_addr(attrs.get("FULL_ADDR")),
                },
            })
            shipped += 1
        if shipped < floor:
            raise SystemExit("%s ships %d sites (floor %d, %d placeless rows "
                             "skipped) — the layer shrank; read the change "
                             "before moving the floor"
                             % (layer_url, shipped, floor, skipped))
        counts[kind] = (shipped, skipped)

    features.sort(key=lambda f: (f["properties"]["name"].lower(),
                                 f["properties"]["kind"]))
    no_addr = sum(1 for f in features if not f["properties"]["address"])
    if no_addr > len(features) * 0.02:
        raise SystemExit("%d of %d sites carry no address — FULL_ADDR moved"
                         % (no_addr, len(features)))

    with open(OUT_PATH, "w") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f,
                  ensure_ascii=False, separators=(",", ":"))
    print("wrote %d school sites (%s) -> %s"
          % (len(features),
             ", ".join("%s %d shipped / %d placeless skipped" % (k, v[0], v[1])
                       for k, v in sorted(counts.items())),
             os.path.relpath(OUT_PATH, REPO_ROOT)))


if __name__ == "__main__":
    sys.exit(main())
