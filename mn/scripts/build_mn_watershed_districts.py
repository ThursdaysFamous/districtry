#!/usr/bin/env python3
"""
Build data/app/mn-watershed-districts.json — every watershed district and
watershed management organization in Minnesota, as the state's Board of
Water and Soil Resources (BWSR) draws them.

WHAT THESE ARE, AND WHY THEY ARE A LEVEL OF GOVERNMENT. Minnesota law
creates two kinds of body to manage water by watershed rather than by
county line, and both can put a charge on a property tax bill:

  * a WATERSHED DISTRICT (Minn. Stat. ch. 103D) is a special-purpose local
    government with its own board of managers, appointed by the county
    boards of the counties it lies in (103D.311), and its own levy;
  * a WATERSHED MANAGEMENT ORGANIZATION (Minn. Stat. 103B.211 and 103B.231)
    is the Twin Cities metro area's form: a joint-powers board of the cities
    and towns inside it, which the Metropolitan Surface Water Management Act
    requires wherever no watershed district already serves. In three places
    the county itself does that job, and BWSR marks those `COU`.

So this is the "special districts the state's own law creates" level of the
fleet's done standard (docs/DONE_STANDARD.md, entry 12), and it is the one a
reader can see on their own tax statement.

THE SOURCE IS THE STATE'S, READ FROM ITS OWN SERVICE. BWSR publishes the
layer on the Minnesota Geospatial Commons; the shapefile download host
(resources.gisdata.mn.gov) answers robots.txt with `Disallow: /`, measured
2026-10-06, so nothing is fetched from it. The same layer is served as a
public feature service under BWSR's own folder on enterprise.gisdata.mn.gov,
whose robots.txt answers 404 (no policy), and that is what this builder
reads. The layer's own description text still describes a Dakota County
predecessor; the attributes are statewide (45 districts, 16 organizations,
three county-run areas on 2026-10-06) and that is what is measured here.

THE MANAGERS ARE NOT NAMED, AND THAT IS A DECISION ABOUT FORM. Every one of
these boards is APPOINTED — by county boards for a district, by member cities
for an organization, and a county-run area is the county board itself — so a
reader does not vote for any of them. The card names the body, says who
appoints its board, and links the body's own website as BWSR publishes it.

THE PUBLISHER'S POLYGONS OVERLAP IN PLACES AND ARE SHIPPED AS DRAWN. Measured
2026-10-06 with shapely in UTM 15N, 56 pairs touch with more than a square
metre in common. Most are slivers along a shared edge, a few are larger
(Upper Minnesota River and Bois de Sioux share about 25 km2). Nothing here
decides which body is right: the card lists every body the state's map puts
the point in and says so when there is more than one.

GATES, before anything is written:
  1. The feature count is inside a band and every feature is one of the three
     kinds, carrying a name.
  2. Every label ends in its kind's suffix, except the two named in
     LABEL_EXCEPTIONS, each re-checked so an entry cannot outlive its cause.
  3. Every feature's own interior point lies inside its shipped geometry.
  4. 2,000 seeded points across the layer's extent, and 2,000 more across
     the metro bodies' extent, each get the SAME set of
     bodies from the shipped file as from the source, at 99.5% or better,
     and the count of points the source itself places in two bodies is
     printed beside the shipped file's.

Run:  python3 mn/scripts/build_mn_watershed_districts.py
"""

import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
INSTANCE = os.path.dirname(HERE)
FLEET_SCRIPTS = os.path.join(os.path.dirname(INSTANCE), "scripts")
sys.path.insert(0, FLEET_SCRIPTS)

from scraper_common import require_robots_once  # noqa: E402

import mn_vtd_dissolve as vtd  # noqa: E402
from mn_vtd_dissolve import (  # noqa: E402
    point_in_geom, round_coords, simplify,
)

LAYER = ("https://enterprise.gisdata.mn.gov/aghost/rest/services/"
         "us_mn_state_bwsr/bdry_watershed_mgmt_dist_orgs/FeatureServer/0")
QUERY = LAYER + "/query?where=1%3D1&outFields=*&outSR=4326&f=geojson"
USER_AGENT = "districtry/1.0 (+https://districtry.com/mn/)"
REQUEST_TIMEOUT = 120

OUT_FILE = os.path.join(INSTANCE, "data", "app", "mn-watershed-districts.json")

MIN_FEATURES, MAX_FEATURES = 55, 80
SIMPLIFY_TOLERANCE_M = 10.0   # several metro organizations are under 70 km2
                              # and share edges with five neighbours, so the
                              # precinct layers' 40 m would move answers here
SAMPLE_POINTS = 2000
MIN_AGREEMENT = 0.995

KINDS = {
    "WD": ("watershed district", " WD", " Watershed District"),
    "WMO": ("watershed management organization", " WMO",
            " Watershed Management Organization"),
    "COU": ("county-run watershed management", " COU", " Watershed Management"),
}

# Labels the publisher wrote without its kind's suffix. Each is re-checked:
# an entry whose label has since gained the suffix, or that no longer exists,
# fails the build rather than lingering.
LABEL_EXCEPTIONS = {
    "Pioneer-Sarah Creek": "WMO",   # BWSR's label carries a trailing space and no suffix
    "Scott County": "COU",          # the county's own water management area
}


def require_robots(urls):
    vtd.require_robots(urls, FLEET_SCRIPTS)


def fetch():
    import requests  # noqa: PLC0415
    require_robots_once(QUERY, USER_AGENT)
    resp = requests.get(QUERY, headers={"User-Agent": USER_AGENT},
                        timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise SystemExit("FATAL: the service answered an error envelope: %r"
                         % data["error"])
    return data.get("features") or []


def polygons(geom):
    if geom["type"] == "Polygon":
        return [geom["coordinates"]]
    if geom["type"] == "MultiPolygon":
        return geom["coordinates"]
    raise SystemExit("FATAL: unexpected geometry type %r" % geom["type"])


def bbox(geom):
    xs, ys = [], []
    for poly in polygons(geom):
        for ring in poly:
            for x, y in ring:
                xs.append(x)
                ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


def interior_point(geom):
    """The midpoint of the WIDEST interior span across 49 horizontal lines,
    holes included, so the point sits well inside the body rather than on a
    sliver beside an edge (the first-span point the dissolve helper returns
    landed 0.5 m inside South Washington's edge, which simplification then
    moved, and that tests the tolerance rather than the build)."""
    best, best_w = None, 0.0
    for poly in polygons(geom):
        ys = [y for _, y in poly[0]]
        lo, hi = min(ys), max(ys)
        for k in range(1, 50):
            y = lo + (hi - lo) * k / 50.0
            xs = []
            for ring in poly:
                for j in range(len(ring) - 1):
                    (x1, y1), (x2, y2) = ring[j], ring[j + 1]
                    if (y1 > y) != (y2 > y):
                        xs.append(x1 + (x2 - x1) * (y - y1) / (y2 - y1))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                if xs[i + 1] - xs[i] > best_w:
                    best_w, best = xs[i + 1] - xs[i], ((xs[i] + xs[i + 1]) / 2.0, y)
    if best and point_in_geom(best[0], best[1], geom):
        return best
    return None


def names_at(x, y, items):
    out = []
    for name, box, geom in items:
        if box[0] <= x <= box[2] and box[1] <= y <= box[3] and point_in_geom(x, y, geom):
            out.append(name)
    return frozenset(out)


def main():
    raw = fetch()
    if not MIN_FEATURES <= len(raw) <= MAX_FEATURES:
        raise SystemExit("FATAL: the service returned %d features, outside %d-%d"
                         % (len(raw), MIN_FEATURES, MAX_FEATURES))

    seen_exceptions = set()
    features, source_items, shipped_items = [], [], []
    for feature in raw:
        props = feature.get("properties") or {}
        kind = props.get("type")
        if kind not in KINDS:
            raise SystemExit("FATAL: a feature carries type %r, not one of %s"
                             % (kind, sorted(KINDS)))
        label = (props.get("label") or "").strip()
        if not label:
            raise SystemExit("FATAL: a %s feature carries no label" % kind)
        _, suffix, words = KINDS[kind]
        if label.endswith(suffix):
            base = label[:-len(suffix)].strip()
        elif LABEL_EXCEPTIONS.get(label) == kind:
            base = label
            seen_exceptions.add(label)
        else:
            raise SystemExit("FATAL: %r is a %s whose label does not end in %r and "
                             "is not a recorded exception" % (label, kind, suffix))
        name = base + words
        src = feature["geometry"]
        polys = [[simplify(ring, SIMPLIFY_TOLERANCE_M) for ring in poly]
                 for poly in polygons(src)]
        if len(polys) == 1:
            geom = {"type": "Polygon", "coordinates": round_coords(polys[0])}
        else:
            geom = {"type": "MultiPolygon", "coordinates": round_coords(polys)}

        pt = interior_point(src)
        if pt is None:
            raise SystemExit("FATAL: %s has no interior point in its own source "
                             "geometry" % name)
        if not point_in_geom(pt[0], pt[1], geom):
            raise SystemExit("FATAL: %s's own interior point (%.6f, %.6f) falls "
                             "outside its simplified geometry" % (name, pt[0], pt[1]))

        out_props = {
            "name": name,
            "short": base,
            "kind": kind,
            "metro": props.get("metrostate") == "metro",
        }
        # `date_established` is NOT carried. Nothing on the layer says what
        # event the date marks — a district's founding order, or a joint-powers
        # agreement's latest restatement, which for a metro organization is
        # renewed — so a card printing "established" would be asserting one.
        website = (props.get("website") or "").strip()
        if website.startswith("http"):
            out_props["url"] = website
        features.append({"type": "Feature", "properties": out_props, "geometry": geom})
        source_items.append((name, bbox(src), src))
        shipped_items.append((name, bbox(geom), geom))

    stale = set(LABEL_EXCEPTIONS) - seen_exceptions
    if stale:
        raise SystemExit("FATAL: LABEL_EXCEPTIONS names %s, which no longer appear "
                         "without their suffix; remove the entries" % sorted(stale))
    if len({f["properties"]["name"] for f in features}) != len(features):
        raise SystemExit("FATAL: two features derive the same display name")

    # Gate 4 — sampled agreement, as answer SETS so an overlap is compared too.
    # Twice: over the whole layer, and again over the metro bodies alone,
    # because a uniform sample of a 900 km-tall state puts few points in a
    # 20 km2 organization and the metro is where they are small and crowded.
    metro = [b for (n, b, g), f in zip(source_items, features) if f["properties"]["metro"]]
    boxes = [("statewide", [b for _, b, _ in source_items]),
             ("metro", metro)]
    rng = random.Random(20261006)
    for label, bxs in boxes:
        xmin, ymin = min(b[0] for b in bxs), min(b[1] for b in bxs)
        xmax, ymax = max(b[2] for b in bxs), max(b[3] for b in bxs)
        agree = multi_src = multi_out = inside = 0
        for _ in range(SAMPLE_POINTS):
            x, y = rng.uniform(xmin, xmax), rng.uniform(ymin, ymax)
            a = names_at(x, y, source_items)
            b = names_at(x, y, shipped_items)
            agree += a == b
            inside += bool(a)
            multi_src += len(a) > 1
            multi_out += len(b) > 1
        share = agree / float(SAMPLE_POINTS)
        print("agreement (%s): %d/%d sampled points (%.3f%%) get the same bodies; "
              "%d fall in at least one; in two or more: source %d, shipped %d"
              % (label, agree, SAMPLE_POINTS, share * 100, inside, multi_src,
                 multi_out), file=sys.stderr)
        if share < MIN_AGREEMENT:
            raise SystemExit("FATAL: %s agreement %.3f%% is under %.1f%%"
                             % (label, share * 100, MIN_AGREEMENT * 100))

    features.sort(key=lambda f: f["properties"]["name"])
    counts = {}
    for f in features:
        counts[f["properties"]["kind"]] = counts.get(f["properties"]["kind"], 0) + 1
    with open(OUT_FILE, "w", encoding="utf-8") as handle:
        json.dump({"type": "FeatureCollection", "features": features}, handle,
                  separators=(",", ":"))
        handle.write("\n")
    print("mn-watershed-districts -> data/app/%s: %s, %d bytes (dp %.0f m, 6dp)"
          % (os.path.basename(OUT_FILE),
             ", ".join("%d %s" % (counts[k], k) for k in sorted(counts)),
             os.path.getsize(OUT_FILE), SIMPLIFY_TOLERANCE_M), file=sys.stderr)


if __name__ == "__main__":
    main()
