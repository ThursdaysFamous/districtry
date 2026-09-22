#!/usr/bin/env python3
"""
Build ia/data/app/<slug>-county-outline.json for every county an Iowa gap
record NAMES — gap-location geometry, not a coverage test.

WHY THE RULE IS "WHAT A GAP RECORD NAMES" AND NOT "WHAT IS UNSERVED".
scripts/build_coverage_gaps.py refuses a `counties` tag whose outline is
missing, because the Data gaps panel decides whether a gap is where a reader
clicked by fetching exactly that file (`appliesHere` in ia/index.html). A tag
with no outline 404s, `mappable` flips true anyway, and the panel tells a
reader standing inside the gap that nothing is missing where they clicked.
Michigan shipped that state for a few hours on 2026-09-22 and it is what this
file exists to prevent here.

SO THE LIST IS DERIVED FROM THE GAP RECORDS THEMSELVES, which is a tighter
rule than the one mi/scripts/build_mi_gap_outlines.py uses (every unserved
county). Iowa has 80 counties outside its districted supervisor roster and
needs an outline for none of them: an outline nothing names is fetched by
nothing and counted by nothing. It needs one for each county a record does
name, and `--check` FAILS in both directions — a named county with no
outline, and an outline no record names any more.

VERIFICATION IS THE CENSUS'S OWN INTERNAL POINT, the same as Michigan's:
INTPTLAT/INTPTLON is a point the Census guarantees lies inside the county
where a centroid need not, so every county's own point is asserted inside its
outline and outside every other outline this instance ships. Recorded to
data/source so --check needs no network.

Usage:
    python3 ia/scripts/build_ia_gap_outlines.py            # fetch and write
    python3 ia/scripts/build_ia_gap_outlines.py --check    # offline drift gate
    python3 ia/scripts/build_ia_gap_outlines.py --list     # the derived list
"""

import argparse
import datetime
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
GAPS = os.path.join(APP, "coverage-gaps.json")
# This instance's key in the guidebook gaps block (its worksheet's
# `this_metro`), which is what the records are filed under.
METRO_KEY = "iowa"
POINTS = os.path.join(INSTANCE, "data", "source", "ia-county-internal-points.json")


def fail(msg):
    print("build-ia-gap-outlines: FAIL — " + msg, file=sys.stderr)
    sys.exit(1)


def slug_of(name):
    """A county name as the gap records and the E measure spell it.

    The trailing " County" comes off first: TIGERweb's NAME is "Adair County",
    and the gap records say `adair`. Michigan's builder lost half a build to
    forgetting that, and its 1,225 internal assertions all passed anyway,
    because a self-consistent verification cannot see a naming convention.
    """
    base = name[: -len(" County")] if name.endswith(" County") else name
    return base.lower().replace(".", "").replace(" ", "-")


def named_by_gaps():
    """{slug} — every county this instance owes gap-location geometry.

    TWO INSTANCE-LOCAL READS, AND NO REACH INTO THE ROOT TREE. The obvious
    source is the guidebook's own gap records, and an earlier draft imported
    scripts/build_coverage_gaps.py to read them. scripts/validate_workflow_deps.py
    refused it — a module outside this instance is not a package the
    instance's workflow installs — which is the same fence
    mi/scripts/probe_mi_county_boards.py records when it copies a slug helper
    rather than importing one. So the list is derived from files this
    instance owns:

      the shipped coverage-gaps.json   every county a record already tags,
                                       which keeps an existing outline (Johnson
                                       and Jones) verified on every run;
      ia-county-officers.json          every county whose supervisors that
                                       file withholds, which is where a NEW
                                       gap record comes from.

    The second is what breaks the chicken-and-egg: build_coverage_gaps.py
    refuses to write the shipped file while a record names a county with no
    outline, so a builder reading only that file could never learn about the
    county whose outline is missing. A county stops being withheld when its
    supervisors ship, and `--check` then reports the outline as one no record
    needs any more.
    """
    out = set()
    if os.path.exists(GAPS):
        with open(GAPS, encoding="utf-8") as fh:
            blob = json.load(fh)
        for rec in (blob.values() if isinstance(blob, dict) else blob):
            for slug in rec.get("counties") or []:
                out.add(slug)
    officers = os.path.join(APP, "ia-county-officers.json")
    if os.path.exists(officers):
        with open(officers, encoding="utf-8") as fh:
            for rec in json.load(fh).values():
                if rec.get("supervisorsWithheld") and (rec.get("county") or "").strip():
                    out.add(slug_of(rec["county"].strip()))
    if not out:
        fail("no county is named by a gap record and none has its supervisors "
             "withheld — nothing to build, and that is unexpected enough to stop on")
    return out


def shipped_outlines():
    return {f[: -len("-county-outline.json")]
            for f in os.listdir(APP) if f.endswith("-county-outline.json")}


def fetch(slugs):
    """[(fips, name, lat, lng, rings)] for the named counties, one request."""
    import requests  # noqa: PLC0415 (network only on the build path)
    where = "STATE='%s' AND COUNTY IN (%s)" % (
        STATE_FIPS, ",".join("'%s'" % f for f in sorted(METRO_COUNTY_FIPS)))
    resp = requests.get(TIGERWEB, headers=HEADERS, timeout=REQUEST_TIMEOUT, params={
        "where": where,
        "outFields": "NAME,GEOID,COUNTY,INTPTLAT,INTPTLON",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson",
    })
    resp.raise_for_status()
    feats = (resp.json() or {}).get("features") or []
    if len(feats) != len(METRO_COUNTY_FIPS):
        fail("TIGERweb returned %d counties, expected %d — the query or the "
             "service changed" % (len(feats), len(METRO_COUNTY_FIPS)))
    rows, seen = [], set()
    for feat in feats:
        props = feat.get("properties") or {}
        name = props.get("NAME") or ""
        slug = slug_of(name)
        seen.add(slug)
        if slug not in slugs:
            continue
        try:
            lat, lng = float(props["INTPTLAT"]), float(props["INTPTLON"])
        except (KeyError, TypeError, ValueError):
            fail("%s carries no usable internal point; the whole verification "
                 "rests on it" % name)
        rows.append((props.get("COUNTY"), name, lat, lng, rings_of(feat)))
    missing = sorted(slugs - seen)
    if missing:
        fail("%d county(s) a gap record names are not in the state's own "
             "fabric: %s — check the slug spelling in the record"
             % (len(missing), ", ".join(missing)))
    return sorted(rows)


def outline_geojson(name, geoid, rings):
    simplified = [r for r in (simplify(x) for x in rings) if len(r) >= 4]
    if not simplified:
        fail("%s simplified away to nothing at %d m" % (name, SIMPLIFY_TOLERANCE_M))
    polys = group_rings(simplified)
    geom = ({"type": "Polygon", "coordinates": polys[0]} if len(polys) == 1
            else {"type": "MultiPolygon", "coordinates": polys})
    return {"type": "FeatureCollection",
            "features": [{"type": "Feature",
                          "properties": {"name": name, "geoid": geoid},
                          "geometry": geom}]}


def cross_check(points):
    """Every recorded internal point inside its own outline and outside the rest.

    Run over EVERY outline this instance ships, not only the ones this script
    wrote: Johnson's and Jones's predate it, and an overlap between an old
    outline and a new one is exactly the kind of thing a scoped check misses.
    """
    rings = {}
    for slug in shipped_outlines():
        with open(os.path.join(APP, slug + "-county-outline.json"),
                  encoding="utf-8") as fh:
            doc = json.load(fh)
        feat = (doc.get("features") or [None])[0]
        rings[slug] = rings_of(feat) if feat else []
    problems = []
    for slug, pt in sorted(points.items()):
        for other, rs in sorted(rings.items()):
            inside = point_in_rings(pt["lat"], pt["lng"], rs)
            if other == slug and not inside:
                problems.append("%s: its own Census internal point is not "
                                "inside the built outline" % slug)
            elif other != slug and inside:
                problems.append("%s: %s's outline swallows its internal point "
                                "— one of the two is wrong" % (slug, other))
    return problems, len(rings)


def check():
    want = named_by_gaps()
    have = shipped_outlines()
    missing = sorted(want - have)
    if missing:
        fail("%d county(s) named by a gap record have no outline: %s — the "
             "panel would 404 on each and claim a clean spot there"
             % (len(missing), ", ".join(missing)))
    if not os.path.exists(POINTS):
        fail("%s is missing — run the builder; --check cannot verify geometry "
             "without the internal points the build recorded"
             % os.path.relpath(POINTS, INSTANCE))
    with open(POINTS, encoding="utf-8") as fh:
        recorded = json.load(fh)
    points = recorded["points"]
    stale = sorted(set(points) - want)
    if stale:
        fail("%d recorded county(s) are named by no gap record any more (%s) — "
             "if the gap closed, retire the outline and this record with it"
             % (len(stale), ", ".join(stale)))
    unrecorded = sorted(want - set(points))
    if unrecorded:
        fail("%d county(s) are named by a gap record and carry no recorded "
             "internal point (%s) — rebuild" % (len(unrecorded), ", ".join(unrecorded)))
    problems, n = cross_check(points)
    if problems:
        fail("the internal-point cross-check found %d problem(s):\n  %s"
             % (len(problems), "\n  ".join(problems)))
    print("build-ia-gap-outlines: OK — %d county(s) named by a gap record, each "
          "with an outline; every recorded internal point inside its own and "
          "outside the other %d this instance ships (%d assertions), measured %s"
          % (len(want), n - 1, len(points) * n, recorded.get("measured", "?")))


def build():
    want = named_by_gaps()
    have = shipped_outlines()
    todo = want - have
    rows = fetch(want)          # fetch ALL named, so the record covers them all
    points = {}
    for fips, name, lat, lng, rings in rows:
        slug = slug_of(name)
        points[slug] = {"fips": fips, "name": name, "slug": slug,
                        "lat": lat, "lng": lng}
        if slug not in todo:
            continue
        with open(os.path.join(APP, slug + "-county-outline.json"),
                  "w", encoding="utf-8") as fh:
            json.dump(outline_geojson(name, STATE_FIPS + fips, rings), fh,
                      separators=(",", ":"))
            fh.write("\n")
    problems, n = cross_check(points)
    if problems:
        fail("wrote %d outline(s) and the cross-check then found %d problem(s):"
             "\n  %s" % (len(todo), len(problems), "\n  ".join(problems)))
    os.makedirs(os.path.dirname(POINTS), exist_ok=True)
    with open(POINTS, "w", encoding="utf-8") as fh:
        json.dump({"measured": datetime.date.today().isoformat(),
                   "source": TIGERWEB,
                   "note": ("The Census's own internal point per county — "
                            "guaranteed inside, which a centroid is not for a "
                            "concave shape. Recorded so --check runs offline."),
                   "points": points}, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print("build-ia-gap-outlines: wrote %d new outline(s) for %d county(s) named "
          "by a gap record; cross-check %d assertions clean over all %d outlines"
          % (len(todo), len(want), len(points) * n, n))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="offline: gap-named counties vs the shipped outlines")
    ap.add_argument("--list", action="store_true",
                    help="print the counties the gap records name")
    args = ap.parse_args()
    if args.list:
        for s in sorted(named_by_gaps()):
            print(s)
        return
    check() if args.check else build()


if __name__ == "__main__":
    main()
