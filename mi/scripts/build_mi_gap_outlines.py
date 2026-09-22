#!/usr/bin/env python3
"""
Build mi/data/app/<slug>-county-outline.json for every Michigan county this
instance does NOT serve — gap-location geometry, not a coverage test.

WHY THIS EXISTS, and it is a reader-facing bug rather than a tidiness one.
The Data gaps panel answers "is a recorded gap here?" by fetching
`data/app/<slug>-county-outline.json` for each county a gap names
(`appliesHere` in mi/index.html). Michigan shipped `counties` arrays with no
outlines behind them for a few hours on 2026-09-22, and the panel's own
`mappable` flag flips TRUE the moment any gap names a county. With every
fetch 404ing, `here` stayed empty while `mappable` said the panel could
locate things, so the lede fell to:

    "Nothing recorded is missing where you clicked."

told to a reader standing in one of the 35 counties whose board this app
cannot answer. Four of those county seats -- Munising, Cadillac, Corunna,
Bessemer -- were point-in-polygoned against Michigan's own coverage wash and
all four are inside it. The branch's sibling comment already says why that
must never happen: "Neither may claim their spot is clean."

SO A `counties` TAG IS A PROMISE THE PANEL CAN LOCATE THAT COUNTY, and this
script is how Michigan keeps it.

THE COUNTY LIST IS DERIVED, NEVER KEPT BY HAND. The unserved counties are
METRO_COUNTY_FIPS minus the counties `mi-commissioner-members.json` covers --
the same `served` set scripts/build_eam_status.py computes for E. A roster
tranche therefore shrinks this list on its own, and a county that ships stops
needing a gap outline without anyone remembering to remove it. `--check`
FAILS on an outline for a county that has since been served, so the two
cannot drift.

VERIFICATION USES THE CENSUS'S OWN INTERNAL POINT, not hand-picked anchors.
Illinois's scripts/build_county_outline.py carries per-county `inside` and
`outside` coordinates, geocoded by hand; at 35 counties that is 35 chances to
mistype a coordinate and have the mistake read as data. TIGERweb publishes
INTPTLAT/INTPTLON per county -- a point the Census guarantees lies inside
that county, including for the concave and multi-part shapes where a centroid
does not. So the test is: every county's own internal point falls INSIDE its
built ring, and OUTSIDE all 34 others. That is 35 x 35 = 1,225 assertions
that need no judgement from me, and it catches the failure hand anchors are
meant to catch (a boundary that swallowed a neighbour) plus one they cannot
(two counties built from the same geometry).

WATER IS INCLUDED, deliberately. TIGERweb's Michigan county fabric is
water-inclusive -- mi/scripts/build_metro_outline.py's own note records
Keweenaw spanning 2.57 degrees of longitude, out past Isle Royale. The
coverage wash is built from that same fabric, so clipping these to land would
make a gap outline and the wash disagree about where a county is, and a
reader clicking lake water inside the wash would fall through the gap test
for a county that water belongs to.

Usage:
    python3 mi/scripts/build_mi_gap_outlines.py            # fetch and write
    python3 mi/scripts/build_mi_gap_outlines.py --check    # offline drift gate
    python3 mi/scripts/build_mi_gap_outlines.py --list     # the derived list
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build_metro_outline import (  # noqa: E402  (shared machinery — do not fork)
    HEADERS, METRO_COUNTY_FIPS, REQUEST_TIMEOUT, SIMPLIFY_TOLERANCE_M,
    STATE_FIPS, TIGERWEB, group_rings, point_in_rings, rings_of, simplify,
)

INSTANCE = os.path.dirname(HERE)
APP = os.path.join(INSTANCE, "data", "app")
ROSTER = os.path.join(APP, "mi-commissioner-members.json")
# The internal points the build verified against, so --check can re-run the
# same 35x35 test with no network. Source data, not served to anyone.
POINTS = os.path.join(INSTANCE, "data", "source", "mi-county-internal-points.json")


def fail(msg):
    print("build-mi-gap-outlines: FAIL — " + msg, file=sys.stderr)
    sys.exit(1)


def slug_of(name):
    """A county name as the gap records and the E measure spell it.

    THE TRAILING " County" COMES OFF FIRST, and the first draft of this file
    forgot to. TIGERweb's NAME field is "Alger County", not "Alger", so the
    plain rule produced `alger-county` and wrote
    `alger-county-county-outline.json` -- a file the panel never fetches,
    under a slug no gap record names. The 1,225-assertion cross-check below
    passed it without complaint, because the outlines were perfectly
    consistent WITH EACH OTHER; nothing in a self-consistent verification can
    see a naming convention. What caught it was comparing the built slugs to
    the ones Michigan's own gap records use, which is why
    check_slugs_match_gap_records() now runs on the build path.

    Then the plain rule mi/scripts/probe_mi_county_boards.py states: lower,
    drop full stops, spaces to hyphens. Michigan has no county name needing
    the `De Witt` override Illinois carries.
    """
    base = name[: -len(" County")] if name.endswith(" County") else name
    return base.lower().replace(".", "").replace(" ", "-")


def check_slugs_match_gap_records(slugs):
    """The built slugs must be the ones the gap records actually name.

    The cross-check proves the geometry is right about itself. This proves it
    is right about the CONSUMER, which is a different question and the one
    the first draft got wrong -- `alger-county` instead of `alger`, 35 files
    the panel would never have fetched, every internal assertion green.

    It is vacuous while no gap record names a county, which was Michigan's
    state until the `counties` arrays landed, and it says so rather than
    printing a pass it has not earned.
    """
    gaps_path = os.path.join(APP, "coverage-gaps.json")
    if not os.path.exists(gaps_path):
        return "no coverage-gaps.json — slug agreement UNCHECKED"
    with open(gaps_path, encoding="utf-8") as fh:
        blob = json.load(fh)
    records = blob.values() if isinstance(blob, dict) else blob
    named = set()
    for rec in records:
        for slug in rec.get("counties") or []:
            named.add(slug)
    if not named:
        return ("no gap record names a county yet — slug agreement UNCHECKED, "
                "and it becomes live the moment one does")
    missing = sorted(named - set(slugs))
    extra = sorted(set(slugs) - named)
    if missing:
        fail("%d county(s) are named by a gap record and have no outline under "
             "that slug: %s — the panel fetches "
             "data/app/<slug>-county-outline.json and would 404 on each"
             % (len(missing), ", ".join(missing)))
    if extra:
        fail("%d outline(s) are built under a slug no gap record names: %s — "
             "either the slug is wrong or the record is missing its county"
             % (len(extra), ", ".join(extra)))
    return "slugs agree with all %d counties the gap records name" % len(named)


def served_fips():
    """County FIPS the commissioner roster covers — the same set E calls served."""
    if not os.path.exists(ROSTER):
        fail("%s is missing; the unserved list is derived from it and cannot "
             "be guessed" % os.path.relpath(ROSTER, INSTANCE))
    with open(ROSTER, encoding="utf-8") as fh:
        roster = json.load(fh)
    return set(roster)


def unserved_fips():
    served = served_fips()
    stray = served - set(METRO_COUNTY_FIPS)
    if stray:
        fail("the roster names county FIPS the state fabric does not: %s"
             % ", ".join(sorted(stray)))
    out = sorted(set(METRO_COUNTY_FIPS) - served)
    if not out:
        print("build-mi-gap-outlines: every county is served — nothing to build")
    return out


def fetch(fips_list):
    """[(fips, name, intpt_lat, intpt_lng, rings)] from TIGERweb, one request."""
    import requests  # noqa: PLC0415 (network only on the build path)
    where = "STATE='%s' AND COUNTY IN (%s)" % (
        STATE_FIPS, ",".join("'%s'" % f for f in fips_list))
    resp = requests.get(TIGERWEB, headers=HEADERS, timeout=REQUEST_TIMEOUT, params={
        "where": where,
        "outFields": "NAME,GEOID,COUNTY,INTPTLAT,INTPTLON",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson",
    })
    resp.raise_for_status()
    feats = (resp.json() or {}).get("features") or []
    if len(feats) != len(fips_list):
        fail("TIGERweb returned %d counties, expected %d — the query or the "
             "service changed" % (len(feats), len(fips_list)))
    out = []
    for feat in feats:
        props = feat.get("properties") or {}
        fips, name = props.get("COUNTY"), props.get("NAME")
        try:
            lat, lng = float(props["INTPTLAT"]), float(props["INTPTLON"])
        except (KeyError, TypeError, ValueError):
            fail("%s County carries no usable INTPTLAT/INTPTLON; the whole "
                 "verification rests on it" % name)
        rings = rings_of(feat)
        if not fips or not name or not rings:
            fail("TIGERweb returned a county with no FIPS, name or geometry: %r"
                 % (props,))
        out.append((fips, name, lat, lng, rings))
    return sorted(out)


def outline_geojson(name, geoid, rings):
    """One Feature, simplified, holes nested — the shape the panel reads."""
    simplified = [simplify(r) for r in rings]
    simplified = [r for r in simplified if len(r) >= 4]
    if not simplified:
        fail("%s simplified away to nothing at %d m" % (name, SIMPLIFY_TOLERANCE_M))
    polys = group_rings(simplified)
    geom = ({"type": "Polygon", "coordinates": polys[0]} if len(polys) == 1
            else {"type": "MultiPolygon", "coordinates": polys})
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"name": name, "geoid": geoid},
            "geometry": geom,
        }],
    }


def all_rings(doc):
    feat = (doc.get("features") or [None])[0]
    return rings_of(feat) if feat else []


def cross_check(built, points):
    """Every county's internal point inside its own ring and outside the rest.

    The whole verification, and it is deliberately not a sample: a boundary
    that swallowed a neighbour shows up as that neighbour's point landing in
    two counties, and two counties accidentally built from one geometry show
    up the same way. Hand-picked anchors catch the first and miss the second.
    """
    problems = []
    for slug, doc in sorted(built.items()):
        rings = all_rings(doc)
        for other, pt in sorted(points.items()):
            inside = point_in_rings(pt["lat"], pt["lng"], rings)
            if other == slug and not inside:
                problems.append(
                    "%s: the Census's own internal point for it (%.5f, %.5f) "
                    "is NOT inside the built outline" % (slug, pt["lat"], pt["lng"]))
            elif other != slug and inside:
                problems.append(
                    "%s: swallows %s's internal point (%.5f, %.5f) — one of the "
                    "two outlines is wrong" % (slug, other, pt["lat"], pt["lng"]))
    return problems


def load_built():
    """{slug: doc} for every gap outline on disk."""
    out = {}
    for fname in sorted(os.listdir(APP)):
        if not fname.endswith("-county-outline.json"):
            continue
        slug = fname[: -len("-county-outline.json")]
        with open(os.path.join(APP, fname), encoding="utf-8") as fh:
            out[slug] = json.load(fh)
    return out


def check():
    """Offline: the shipped outlines still match the derived list and pass 35x35."""
    want = unserved_fips()
    if not os.path.exists(POINTS):
        fail("%s is missing — run the builder; --check cannot verify geometry "
             "without the internal points the build recorded"
             % os.path.relpath(POINTS, INSTANCE))
    with open(POINTS, encoding="utf-8") as fh:
        recorded = json.load(fh)
    points = recorded["points"]
    built = load_built()

    want_slugs = {points[s]["slug"] if s in points else s for s in points}
    by_fips = {v["fips"]: s for s, v in points.items()}
    missing_fips = [f for f in want if f not in by_fips]
    extra_fips = [f for f in by_fips if f not in want]
    if missing_fips:
        fail("%d unserved county(s) have no recorded internal point (%s) — a "
             "roster tranche removed a county from the served set, so rebuild"
             % (len(missing_fips), ", ".join(missing_fips)))
    if extra_fips:
        fail("%d recorded county(s) are now SERVED and should no longer carry a "
             "gap outline (%s) — rebuild, and drop the worksheet entries"
             % (len(extra_fips), ", ".join(sorted(
                 "%s/%s" % (f, by_fips[f]) for f in extra_fips))))

    absent = sorted(s for s in points if s not in built)
    if absent:
        fail("%d county(s) are recorded and have no outline file: %s"
             % (len(absent), ", ".join(absent)))

    scoped = {s: built[s] for s in points}
    problems = cross_check(scoped, points)
    if problems:
        fail("the internal-point cross-check found %d problem(s):\n  %s"
             % (len(problems), "\n  ".join(problems)))
    slug_note = check_slugs_match_gap_records(scoped)

    print("build-mi-gap-outlines: OK — %d gap outline(s) for the %d unserved "
          "counties, every county's own Census internal point inside its outline "
          "and outside all %d others (%d assertions), measured %s; %s"
          % (len(scoped), len(want), len(scoped) - 1,
             len(scoped) * len(points), recorded.get("measured", "?"), slug_note))
    return want_slugs


def build():
    import datetime
    want = unserved_fips()
    if not want:
        return
    rows = fetch(want)
    built, points = {}, {}
    for fips, name, lat, lng, rings in rows:
        slug = slug_of(name)
        built[slug] = outline_geojson(name, STATE_FIPS + fips, rings)
        points[slug] = {"fips": fips, "name": name, "slug": slug,
                        "lat": lat, "lng": lng}

    problems = cross_check(built, points)
    if problems:
        fail("refusing to write — the internal-point cross-check found %d "
             "problem(s):\n  %s" % (len(problems), "\n  ".join(problems)))
    slug_note = check_slugs_match_gap_records(built)

    for slug, doc in sorted(built.items()):
        path = os.path.join(APP, slug + "-county-outline.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, separators=(",", ":"))
            fh.write("\n")
    os.makedirs(os.path.dirname(POINTS), exist_ok=True)
    with open(POINTS, "w", encoding="utf-8") as fh:
        json.dump({
            "measured": datetime.date.today().isoformat(),
            "source": TIGERWEB,
            "note": ("The Census's own INTPTLAT/INTPTLON per county — a point "
                     "guaranteed to lie inside that county, which a centroid is "
                     "not for a concave or multi-part shape. Recorded so --check "
                     "can re-run the same cross-check offline."),
            "points": points,
        }, fh, indent=1, sort_keys=True)
        fh.write("\n")

    total = sum(os.path.getsize(os.path.join(APP, s + "-county-outline.json"))
                for s in built)
    print("build-mi-gap-outlines: wrote %d outline(s), %.1f KB total, "
          "cross-check %d assertions clean; %s"
          % (len(built), total / 1024.0, len(built) * len(points), slug_note))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="offline: shipped outlines vs the derived county list")
    ap.add_argument("--list", action="store_true",
                    help="print the derived unserved-county list and stop")
    args = ap.parse_args()
    if args.list:
        for f in unserved_fips():
            print(f)
        return
    if args.check:
        check()
        return
    build()


if __name__ == "__main__":
    main()
