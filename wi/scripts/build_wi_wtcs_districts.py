#!/usr/bin/env python3
"""
Build data/app/wtcs-districts.json — Wisconsin's 16 technical college
districts (phase 4 PR 6, docs/WI_PHASE4_PLAN.md's stretch item).

THE CONCEPT IS IDENTITY-ONLY BY STATUTE: every point in Wisconsin sits in
exactly one Wisconsin Technical College System district and funds it
through its property tax, but the district BOARD IS APPOINTED (Wis. Stat.
38.08 — appointment committees of county board chairs / school board
presidents, not voters), so the card labels the board appointed and names
no one, exactly as the phase-2 research recorded (Leg. Council special
purpose district brief). Inventing an electoral story here is the harm
the honesty rules exist to prevent.

SOURCE: DPI's own org (the shipped school-site and library builds' org,
same reference-use licence posture — "intended for your reference use
only", no redistribution ban; AGO item 0fdad1436fc04ebf85ba7839dad3ab79,
registered in validate_sources for the successor watch). The layer is
titled 2019 and is CURRENT despite the name: it carries "Northwood
Technical College District", the 2021 rename of WITC, and the item was
modified 2025-02 — the LTSB title-vs-URL vintage lesson, read the
content. wtcs.edu itself was UNREACHABLE from the build environment at
first build (proxy CONNECT 502 — a sandbox-side fact, per the WEC probe's
lesson), so the witnesses below are the layer's own structure; the
monthly source report watches the DPI item.

GATES, each a measurement made 2026-08-27 and not an assumption:

  * exactly 16 features, names and abbreviations distinct, every name
    ending "Technical College District", every coordinate in the state
    envelope;
  * THE SEAT WITNESS: each district must contain its own college's home
    city — sixteen pinned points, verified 16/16 against the fetched
    geometry before they were pinned. This is what catches a mis-drawn,
    mislabeled or swapped district, the failure a bare count never sees;
  * NO OVERLAPS: total pairwise intersection area must stay below 1e-3
    square degrees (measured 2.3e-9 at full precision and 2.1e-4 on the
    shipped server-generalized fabric, whose per-feature ~55 m offset
    breaks shared-edge vertex identity into slivers). The published
    geometry contains a self-intersection, so the GATE math runs on
    make_valid copies; what SHIPS is the server's geometry as answered;
  * NO HOLES EXCEPT LAKE WINNEBAGO: the union of the 16 has exactly one
    material interior hole, and it is Lake Winnebago (centroid
    44.02,-88.41, ~0.0599 deg²) — honestly inside no district, like the
    Great Lakes outside the union, so a reader clicking the lake gets
    the standard empty state and that is the true answer. The gate
    REQUIRES that hole present (its absence means the fabric was
    redrawn — re-measure) and every other hole to total under 1e-3 deg²
    (measured 1.1e-4 on the generalized fabric — the same edge slivers).
    (A first gate draft sampled the STATE OUTLINE and "found" 43 holes
    that were all open Great Lakes water; a second sampled the TIGER
    school-district fabric, which carries the same lake water. TIGER
    geographies include territorial water — test a tiling's integrity
    from its own union, not from a water-bearing reference.)

  * NO NESTED SHELLS, and a FLOOR ON INTERIOR RINGS. Added 2026-09-05,
    and the reason is that every gate above was blind to a wrong answer
    this file shipped for a week.

THE HOLE THIS BUILDER FILLED, AND WHY NOTHING CAUGHT IT.

ArcGIS's GeoJSON export silently UNNESTS interior rings: it returns a
feature's holes as separate PARTS, so ground the publisher cut out of a
district becomes ground the district claims. Measured on this layer's own
endpoint, same query, same generalization, only the format changed:
`f=geojson` returns the 16 districts with ZERO interior rings, `f=json`
returns the same 16 with 109. The part counts say it plainly — Madison
came back as 55 parts and 27, Southwest as 40 and 21, Blackhawk as 9 and
4; every missing hole is an extra part.

THE LAKE WINNEBAGO GATE ABOVE CANNOT SEE THIS, and it is blind by
construction rather than merely unlucky — which matters, because it was
written BECAUSE holes matter here:

  1. it runs at the UNION level on make_valid copies, and shapely's
     make_valid RE-NESTS an unnested inner shell as a hole. Measured: a
     10x10 square with a 2x2 hole gives Polygon/holes=1/area=96.0 from
     both the nested form and the unnested one, so the two fetches are
     the same object by the time any gate downstream of make_valid looks
     (112 union holes either way);
  2. these districts TILE the state, so a hole in one district is
     usually another district and the UNION fills it from the neighbour
     regardless of format. A union-level hole count says nothing about
     per-feature holes even without (1).

So the two gates added here run on the geometry as SHIPPED, before any
make_valid. The nested-shell test is the stronger of the two: a part
inside a part is never lawful — two disjoint pieces of one district
cannot contain one another — so it catches the unnesting whatever
produced it, without pinning a count or assuming the upstream bug
persists. The ring floor catches the other failure, holes dropped
outright rather than unnested.

WHAT A READER SAW, measured at an interior point of each source hole
(never a centroid: the centroid of a non-convex hole falls outside it,
lands in the owner's shell and reads as agreement):

  109 interior rings at source; 103 enclose real ground and 6 are
  zero-area 4-vertex artifacts of the generalization. Of the 103, the
  shipped file named TWO colleges at 100 points and named one where the
  source names none at 3. None agreed. 27.9 km² of holes, six over
  1 km², the largest 2.26 km².

  The CARD count is smaller and is the one to quote to a reader: the app
  renders the FIRST containing feature, so at 44 of the 103 file order
  already showed the true district and a reader saw the right answer
  from a wrong geometry. The card's answer changes at 59, three of them
  onto "no district".

  Unlike the county supervisory rebuild there is NO RESIDUAL: that file
  is mapshaper-simplified at 9% retain, which drops small rings in both
  versions, while this builder ships the server's geometry as answered.
  All 103 are fixed.
"""

import json
import os
import subprocess
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
OUT = os.path.join(REPO_ROOT, "data", "app", "wtcs-districts.json")

LAYER = ("https://services8.arcgis.com/o4NJgD3NfeHnWy06/arcgis/rest/services/"
         "WI_Technical_College_Regions_2019/FeatureServer/0/query"
         "?where=1%3D1&outFields=WTCR_ABV,WTC_REGION&outSR=4326"
         # server-generalized (the ward-overlay precedent): full precision
         # is 9.2 MB for 16 features; ~55 m offset ships 316 KB. Per-feature
         # generalization breaks shared-edge vertex identity, so the fabric
         # gates below carry sliver tolerances measured at THIS precision.
         "&maxAllowableOffset=0.0005&geometryPrecision=4&f=json")
WI_BBOX = (-92.95, 42.40, -86.20, 47.40)

# Each district's own college home city — every pin verified against the
# fetched geometry 2026-08-27 (16/16) before being pinned here.
SEATS = {
    "BH": ("Janesville", 42.6828, -89.0187),
    "CV": ("Eau Claire", 44.8113, -91.4985),
    "FV": ("Appleton", 44.2619, -88.4154),
    "GW": ("Kenosha", 42.5847, -87.8212),
    "LS": ("Sheboygan", 43.7508, -87.7145),
    "MA": ("Madison", 43.0731, -89.4012),
    "MS": ("Wisconsin Rapids", 44.3836, -89.8174),
    "MI": ("Milwaukee", 43.0389, -87.9065),
    "MP": ("Fond du Lac", 43.7730, -88.4470),
    "NI": ("Rhinelander", 45.6366, -89.4121),
    "NC": ("Wausau", 44.9591, -89.6301),
    "NE": ("Green Bay", 44.5133, -88.0133),
    "NT": ("Rice Lake", 45.5061, -91.7382),
    "SW": ("Fennimore", 42.9797, -90.6540),
    "WA": ("Pewaukee", 43.0806, -88.2612),
    "WW": ("La Crosse", 43.8014, -91.2396),
}
WINNEBAGO = (44.02, -88.41)   # the one lawful hole's centroid
WINNEBAGO_AREA = 0.0599       # deg², measured 2026-08-27

# Interior rings across the 16 districts, measured 2026-09-05 through f=json:
# 109, of which 103 enclose real ground and 6 are zero-area 4-vertex artifacts
# of the server generalization. The floor sits below the measurement so a
# boundary amendment does not fail the build, and far above the 0 that
# f=geojson returns.
HOLE_MEASURED = 109
HOLE_FLOOR = 90

# Parts sitting inside another part of the same district, after excluding the
# one lawful case (a part inside a HOLE of another part — Madison's enclave).
# Measured 2026-09-05: 6, one in Fox Valley and five in Northeast, every one a
# 4-vertex micro-part of at most 1.5e-8 deg² that the server generalization
# emits. They are NOT separable from real holes by area or vertex count — see
# nested_shells — so the number is pinned rather than tolerated by shape, and
# a rise is a thing to read rather than to re-pin.
NESTED_SHELL_ARTIFACTS = 6


def esri_feature_to_geojson(f):
    """Esri JSON -> GeoJSON, nesting each interior ring inside its owner.

    The converter lives in build_wi_supervisory_districts, which is where the
    exporter defect was first measured; it is imported rather than copied so
    the two builders cannot drift on the containment rule.
    """
    sys.path.insert(0, SCRIPT_DIR)
    from build_wi_supervisory_districts import _esri_feature_to_geojson
    return _esri_feature_to_geojson(f)


def interior_rings(geom):
    """Every interior ring in a GeoJSON Polygon/MultiPolygon."""
    polys = ([geom["coordinates"]] if geom["type"] == "Polygon"
             else geom["coordinates"])
    return [r for p in polys for r in p[1:]]


def nested_shells(geom, contains):
    """Parts whose shell sits inside another part's shell, minus the lawful ones.

    `f=geojson` returns a feature's holes as separate PARTS, so a shell inside
    a shell is the defect's own signature. ONE containment is lawful and is
    excluded structurally: a part sitting inside a HOLE of another part is a
    genuine enclave, not an unnested ring.

    THIS IS A SECOND OPINION, NOT THE GATE. A zero-tolerance version was
    written first and it does not survive contact with the data: the server
    generalization emits degenerate micro-parts, and they are not separable
    from real holes by any shape test tried. Area fails — 22 of the 103 real
    interior rings are smaller than the largest such micro-part, so a
    threshold clearing the noise would blind the gate to 22 real holes.
    Vertex count fails — every micro-part has 4 vertices and so do 29 of the
    real rings. So the count is pinned to what was MEASURED (see
    NESTED_SHELL_ARTIFACTS) and a rise is the news; the interior-ring FLOOR
    is what actually catches an unnested fetch, which shows up there as 0.
    """
    if geom["type"] == "Polygon":
        return []
    parts = geom["coordinates"]
    out = []
    for i, a in enumerate(parts):
        for j, b in enumerate(parts):
            if i == j or not contains(a[0], b[0]):
                continue
            if any(contains(h, b[0]) for h in a[1:]):
                continue            # inside a hole of a — a lawful enclave
            out.append(j)
    return out


def fetch(url, tries=6, timeout=120):
    last = None
    for _ in range(tries):
        try:
            return subprocess.run(
                ["curl", "-sSL", "--fail", "--max-time", str(timeout),
                 "-H", "User-Agent: districtry/1.0 (+https://districtry.com/wi/)",
                 url],
                check=True, capture_output=True).stdout
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2)
    raise last


def main():
    from shapely.geometry import shape, Point, Polygon
    from shapely.ops import unary_union
    from shapely import make_valid

    def poly_only(g):
        # make_valid on generalized polygons can emit a GeometryCollection
        # carrying degenerate lines/points beside the real polygons
        if g.geom_type == "GeometryCollection":
            return unary_union([p for p in g.geoms
                                if p.geom_type in ("Polygon", "MultiPolygon")])
        return g

    doc = json.loads(fetch(LAYER))
    if isinstance(doc, dict) and doc.get("error"):
        raise SystemExit("ArcGIS error from the WTCS layer: %r" % doc["error"])
    feats = [esri_feature_to_geojson(f) for f in (doc.get("features") or [])]
    if len(feats) != 16:
        raise SystemExit("expected exactly 16 WTCS districts, got %d — the "
                         "system reorganized; re-measure" % len(feats))
    names, abbrevs = set(), set()
    out_feats, valid_shapes = [], {}
    for f in feats:
        p = f["properties"]
        name = str(p.get("WTC_REGION") or "").strip()
        ab = str(p.get("WTCR_ABV") or "").strip()
        if not name.endswith("Technical College District"):
            raise SystemExit("district name %r does not end 'Technical "
                             "College District' — the schema moved" % name)
        if not ab or name in names or ab in abbrevs:
            raise SystemExit("duplicate or empty name/abbrev (%r / %r)"
                             % (name, ab))
        names.add(name)
        abbrevs.add(ab)
        out_feats.append({"type": "Feature",
                          "properties": {"NAME": name, "ABBREV": ab},
                          "geometry": f["geometry"]})
        valid_shapes[ab] = poly_only(make_valid(shape(f["geometry"])))
        stack = [f["geometry"]["coordinates"]]
        while stack:
            v = stack.pop()
            if isinstance(v[0], (int, float)):
                if not (WI_BBOX[0] < v[0] < WI_BBOX[2]
                        and WI_BBOX[1] < v[1] < WI_BBOX[3]):
                    raise SystemExit("%s carries a coordinate outside the "
                                     "state envelope — outSR ignored?" % name)
            else:
                stack.extend(v)

    if set(valid_shapes) != set(SEATS):
        raise SystemExit("abbreviation set changed: layer %s vs pinned %s"
                         % (sorted(valid_shapes), sorted(SEATS)))
    for ab, (city, lat, lng) in SEATS.items():
        hits = [a for a, s in valid_shapes.items()
                if s.contains(Point(lng, lat))]
        if hits != [ab]:
            raise SystemExit("seat witness failed: %s (%s) lands in %s, not "
                             "[%s] — a district moved or is mislabeled"
                             % (city, ab, hits, ab))

    # ---- THE PER-FEATURE HOLE GATES -------------------------------------
    # Both run on out_feats — the geometry as SHIPPED — and NOT on the
    # make_valid copies the gates below use, because shapely's make_valid
    # RE-NESTS an unnested inner shell as a hole. Measured 2026-09-05: a
    # 10x10 square with a 2x2 hole gives Polygon/holes=1/area=96.0 from both
    # the properly nested form and the unnested one, so every gate downstream
    # of make_valid is blind to this by construction. The union-level Lake
    # Winnebago gate is doubly blind: these districts TILE the state, so a
    # hole in one is usually another district and the union fills it from the
    # neighbour whatever the fetch returned.
    def ring_contains(outer, pt_ring):
        from build_wi_supervisory_districts import _ring_contains
        probes = [pt_ring[0], pt_ring[len(pt_ring) // 3],
                  pt_ring[(2 * len(pt_ring)) // 3]]
        return sum(1 for pt in probes if _ring_contains(outer, pt)) >= 2

    nested = {f["properties"]["ABBREV"]: nested_shells(f["geometry"], ring_contains)
              for f in out_feats}
    n_nested = sum(len(v) for v in nested.values())
    if n_nested > NESTED_SHELL_ARTIFACTS:
        raise SystemExit(
            "%d parts sit inside another part of their own district, above "
            "the %d measured on 2026-09-05 (%s). A part inside a part is what "
            "the GeoJSON exporter makes of a hole, so this is either an "
            "unnested fetch or new generalization noise — read them before "
            "moving the pin; do not ship."
            % (n_nested, NESTED_SHELL_ARTIFACTS,
               ", ".join("%s:%d" % (k, len(v)) for k, v in sorted(nested.items()) if v)))

    holes_shipped = sum(len(interior_rings(f["geometry"])) for f in out_feats)
    if holes_shipped < HOLE_FLOOR:
        raise SystemExit(
            "the 16 districts carry %d interior rings, under the floor of %d "
            "(measured %d on 2026-09-05) — the publisher's own cutouts have "
            "gone missing, which is what f=geojson does silently; do not ship"
            % (holes_shipped, HOLE_FLOOR, HOLE_MEASURED))

    abs_ = sorted(valid_shapes)
    overlap = 0.0
    for i in range(len(abs_)):
        for j in range(i + 1, len(abs_)):
            a, b = valid_shapes[abs_[i]], valid_shapes[abs_[j]]
            if a.intersects(b):
                overlap += a.intersection(b).area
    if overlap > 1e-3:
        raise SystemExit("districts overlap by %.2e deg² (tolerance 1e-3) — "
                         "the fabric changed; re-measure" % overlap)

    union = poly_only(unary_union(list(valid_shapes.values())))
    geoms = union.geoms if union.geom_type == "MultiPolygon" else [union]
    winnebago = None
    other_holes = 0.0
    for g in geoms:
        for r in g.interiors:
            hole = Polygon(r)
            c = hole.centroid
            if (abs(c.y - WINNEBAGO[0]) < 0.15 and abs(c.x - WINNEBAGO[1]) < 0.15
                    and hole.area > WINNEBAGO_AREA * 0.5):
                winnebago = hole.area
            else:
                other_holes += hole.area
    if winnebago is None:
        raise SystemExit("the Lake Winnebago hole is missing from the union — "
                         "the fabric was redrawn; re-measure before shipping")
    if other_holes > 1e-3:
        raise SystemExit("interior holes beyond Lake Winnebago total %.2e "
                         "deg² (tolerance 1e-3) — a real gap opened between "
                         "districts; do not ship" % other_holes)

    with open(OUT, "w") as f:
        json.dump({"type": "FeatureCollection", "features": out_feats}, f,
                  separators=(",", ":"), ensure_ascii=False)
        f.write("\n")
    print("wrote %s — 16 districts; seat witness 16/16; %d interior rings "
          "shipped (floor %d), %d nested micro-parts (pinned %d); "
          "overlap %.1e deg²; "
          "Lake Winnebago hole %.4f deg² present, other holes %.1e deg²"
          % (os.path.relpath(OUT, REPO_ROOT), holes_shipped, HOLE_FLOOR,
             n_nested, NESTED_SHELL_ARTIFACTS, overlap, winnebago, other_holes),
          file=sys.stderr)


if __name__ == "__main__":
    main()
