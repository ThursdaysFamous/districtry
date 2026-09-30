#!/usr/bin/env python3
"""
Build data/app/ia-school-sites.json — every public school building in Iowa,
as a point FeatureCollection for the school-site nearest-3 card.

SOURCE: the Iowa Legislature's own ArcGIS organization (the same org
county-supervisor and school-district-unified's witness layer already use),
layer IowaSchoolBldgs — 1,321 sites (measured 2026-08-28), all public (no
private-school class in this dataset — its own internal title is
"PublicSchoolBldgs"), native WGS84 (no reprojection needed), licenseInfo
null.

A NAMING TRAP, measured live: the layer's own INTERNAL title is
"PublicSchoolBldgs" — but querying that STRING as a URL slug hits a
COMPLETELY DIFFERENT, unrelated, stale service (title "Public School
Buildings", 1,336 features, last edited 2018-01-12, sparse fields, no
administrator contact at all). The two are easy to confuse because the
wrong one's TITLE matches the right one's NAME. The correct, current layer
is reached only by its own slug, "IowaSchoolBldgs" — pinned as a literal
below, never derived from the title.

PAGINATION IS REQUIRED: the layer's maxRecordCount is 1,000, below its own
1,321-feature count, so a single unpaginated query silently truncates.
Every fetch here pages by resultOffset and asserts the total against the
layer's own returnCountOnly answer.

Unlike Wisconsin's DPI layers, this dataset carries no placeless rows and
no reprojection trap (measured 2026-08-28: all 1,321 records carry
geometry, a physical address, and a school name) — so this builder is
considerably shorter than build_wi_school_sites.py; if a later refresh
finds a placeless or malformed row, that is new information worth a hard
failure, not a silent skip.

The card ships proximity only (name, type, address) — never an
administrator contact, even though the source carries one (Administrator /
Title / Phone / EmailAddress, in-band): Wisconsin's own school-site card
established the precedent of proximity-only for this concept, and matching
it keeps the same concept's card shape consistent across the fleet.

Usage:
    python3 ia/scripts/build_ia_school_sites.py
    python3 ia/scripts/build_ia_school_sites.py --check
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
OUT_PATH = os.path.join(REPO_ROOT, "data", "app", "ia-school-sites.json")

LAYER_URL = "https://services.arcgis.com/vPD5PVLI6sfkZ5E4/arcgis/rest/services/IowaSchoolBldgs/FeatureServer/0"
OUT_FIELDS = "SchoolName,SchoolType,PhysicalStreet,PhyscialCity,ZipCode"
PAGE_SIZE = 1000

EXPECT_FEATURES = 1321

# Iowa's own bounding envelope (METRO_BBOX, ia/metro-worksheet.json) with a
# small margin — a coordinate outside it means outSR was ignored or a
# record is misplaced.
BBOX = {"min_lat": 40.2, "max_lat": 43.6, "min_lng": -96.8, "max_lng": -90.0}


def fetch_json(url):
    require_robots_once(url, UA_STDLIB_DEFAULT, label="ia-build-ia-school-sites")
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def layer_count():
    d = fetch_json(LAYER_URL + "/query?where=1%3D1&returnCountOnly=true&f=json")
    return int(d["count"])


def fetch_all():
    feats = []
    offset = 0
    while True:
        url = (LAYER_URL + "/query?where=1%3D1&outFields=" + OUT_FIELDS +
               "&outSR=4326&f=json&resultOffset=%d&resultRecordCount=%d"
               % (offset, PAGE_SIZE))
        d = fetch_json(url)
        if "error" in d:
            raise SystemExit("%s answered an error: %s" % (LAYER_URL, d["error"]))
        page = d.get("features", [])
        feats.extend(page)
        if len(page) < PAGE_SIZE and not d.get("exceededTransferLimit"):
            return feats
        offset += len(page)


def main():
    check_only = "--check" in sys.argv[1:]

    expected = layer_count()
    if expected != EXPECT_FEATURES:
        raise SystemExit(
            "IowaSchoolBldgs now reports %d features, expected %d — re-verify "
            "before shipping (a count change is real information, not a "
            "floor to silently raise)" % (expected, EXPECT_FEATURES)
        )
    raw = fetch_all()
    if len(raw) != expected:
        raise SystemExit(
            "paged %d features against the layer's own count of %d — the "
            "page cap or a filter ate records" % (len(raw), expected)
        )

    features = []
    for f in raw:
        attrs = f.get("attributes") or {}
        geom = f.get("geometry") or {}
        name = (attrs.get("SchoolName") or "").strip()
        if not name:
            raise SystemExit("a record carries no SchoolName (attrs=%r)" % attrs)
        lng, lat = geom.get("x"), geom.get("y")
        if lng is None or lat is None:
            raise SystemExit("%r carries no geometry — this dataset had none as "
                             "of the build that shipped this script; a placeless "
                             "row is new information, not something to skip "
                             "silently" % name)
        if not (BBOX["min_lat"] <= lat <= BBOX["max_lat"] and
                BBOX["min_lng"] <= lng <= BBOX["max_lng"]):
            raise SystemExit("%r sits at (%s, %s) — outside Iowa's envelope; "
                             "outSR was ignored or the record is misplaced"
                             % (name, lat, lng))
        street = (attrs.get("PhysicalStreet") or "").strip()
        city = (attrs.get("PhyscialCity") or "").strip()
        zip_code = (attrs.get("ZipCode") or "").strip()
        address_bits = [b for b in [street, (city + (", IA " + zip_code if zip_code else "")
                                              if city else None)] if b]
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [round(lng, 6), round(lat, 6)]},
            "properties": {
                "name": name,
                "kind": (attrs.get("SchoolType") or "").strip() or None,
                "address": ", ".join(address_bits) if address_bits else None,
            },
        })

    features.sort(key=lambda f: f["properties"]["name"].lower())

    no_addr = sum(1 for f in features if not f["properties"]["address"])
    if no_addr:
        raise SystemExit("%d of %d sites carry no address — the source shape "
                         "changed" % (no_addr, len(features)))

    payload = json.dumps({"type": "FeatureCollection", "features": features},
                         ensure_ascii=False, separators=(",", ":"))
    if check_only:
        try:
            with open(OUT_PATH) as f:
                shipped = f.read()
        except OSError as e:
            raise SystemExit("data/app/ia-school-sites.json is missing (%s) — "
                             "run this script without --check" % e)
        if shipped != payload:
            raise SystemExit("data/app/ia-school-sites.json has drifted from "
                             "the live layer. Re-run: "
                             "python3 ia/scripts/build_ia_school_sites.py")
        print("check: shipped file matches the live layer (%d sites)" % len(features),
              file=sys.stderr)
        return

    with open(OUT_PATH, "w") as f:
        f.write(payload)
    print("wrote %d school sites -> %s" % (len(features), os.path.relpath(OUT_PATH, REPO_ROOT)),
          file=sys.stderr)


if __name__ == "__main__":
    main()
