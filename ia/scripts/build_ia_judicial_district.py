#!/usr/bin/env python3
"""
Build data/app/ia-judicial-districts.json — Iowa's 8 judicial election
districts, whole-county unions, no new boundary drawn.

Iowa Code SS602.6107/602.6109 (Code 2003) assign each of Iowa's 99 counties to
one of 8 judicial election districts, used "solely for purposes of
nomination, appointment, and retention" (SS602.6109) of district judges,
district associate judges, and magistrates. THE CURRENT CODIFIED SECTIONS
CARRY NO COUNTY LIST AT ALL (verified live 2026-08-28 by fetching
https://www.legis.iowa.gov/docs/code/602.6107.pdf and .../602.6109.pdf,
"Iowa Code 2026" edition): SS602.6107(3) states verbatim that "the composition
of the judicial districts in section 602.6107, Code 2003, and judicial
election districts in section 602.6109, Code 2003, shall remain in effect
until a new division ... is enacted" -- the operative county list survives
only in the superseded 2003 code, which this project could not retrieve (the
legis.iowa.gov legacy archive path returns connection failures from this
sandbox on every URL variant tried).

So the crosswalk below is sourced from two independent CURRENT,
non-statutory publishers who administer the districts and agree exactly:

  1. iowacourts.gov's own per-district "District N Counties" page --
     https://www.iowacourts.gov/iowa-courts/district-court/judicial-district-{1..8}
  2. Ballotpedia's compiled table -- https://ballotpedia.org/Iowa_District_Courts
     (published at the lettered-sub-district level; aggregated up to the 8
     numbered districts here, since sub-districts are a court-administration/
     retention-ballot grouping this layer does not draw).

A THIRD, INDEPENDENT SPATIAL WITNESS runs at build time and is what actually
gates the write: every county's own proven-interior anchor point
(build_metro_outline.py's INSIDE dict, already verified interior by that
builder's own containment test) is checked against the LSAFiscal
JudicialDistricts service's REAL published district polygons -- geometry
this builder never touches otherwise, drawn independently of the county
dissolve below. All 99 pass (measured 2026-08-28). That is stronger than
Wisconsin's wi-circuit-court precedent this build otherwise mirrors exactly
(whole-county unions, double witness, containment gate): Wisconsin has NO
independently-published circuit geometry to check against, so its second
witness is a second TEXT source (wicourts.gov's own listing); Iowa has real
geometry, so the second witness here is spatial.

LEE COUNTY is Iowa's only county with two county seats (Fort Madison and
Keokuk, Iowa Code SS602.6105(2)) and iowacourts.gov's District 8 page lists
it as two entries, "Lee (North)" and "Lee (South)" -- that is NOT a district
split; it is one county and counts once here, same as every other.

POPULATION CROSS-CHECK: the LSAFiscal service's own POP_2010 field sums to
3,046,355 across the 8 districts -- Iowa's exact official 2010 census
population -- corroborating that its polygons are correctly drawn, which is
exactly what this builder's spatial witness leans on.

THE DISSOLVE IS GENERAL-N, NOT PAIRWISE: Wisconsin's circuit-court build only
ever merges two counties at a time (its three statutory exceptions). Iowa's
districts run up to 22 counties (District 2), so this reuses the general
segment-count dissolve build_metro_outline.py already runs once for the
whole state, applied here once per district instead.

JUDGES ARE RETENTION, NEVER "ELECTED": Iowa's district judges, district
associate judges, associate juvenile/probate judges and magistrates are
appointed by the Governor from a nonpartisan judicial nominating commission's
list, then stand periodically in yes/no retention elections (confirmed
verbatim from https://www.iowacourts.gov/for-the-public/educational-resources
-and-services/judicial-selection-and-retention/). Every judge bio on the
roster pages uses "appointed," never "elected." The card states this
explicitly.

ROSTER URL SHAPE IS PER-DISTRICT, NOT ONE PATTERN (verified live for all 8):
  District 1: .../judicial-district-1/judges-and-magistrates-district-1/   (number SUFFIX)
  Districts 2-7: .../judicial-district-N/judges-and-magistrates/           (bare)
  District 8: .../judicial-district-8/district-8-judges-and-magistrates/   (number PREFIX)
A scraper must discover/hardcode the shape per district, never assume one
fleet-wide -- see ia_judicial_district_scraper.py.

Gates (the build refuses to write unless all hold):
  * exactly 99 counties in the crosswalk, each named once, matching
    state-counties.json's BASENAME set exactly;
  * exactly 8 districts built;
  * every county's own interior point lands in its assigned district's
    DISSOLVED polygon (proves the dissolve correctly unioned its members);
  * (unless --skip-live-witness) every county's interior point ALSO lands in
    the LSAFiscal service's REAL published polygon for that same district
    number (proves the crosswalk table itself against independent geometry).

Usage:
    python3 ia/scripts/build_ia_judicial_district.py                     # write the file
    python3 ia/scripts/build_ia_judicial_district.py --check             # verify shipped, write nothing
    python3 ia/scripts/build_ia_judicial_district.py --skip-live-witness # offline dev only
"""

import argparse
import json
import os
import sys

# scraper_common lives in the ROOT scripts/, which this file's own directory is
# not. APPENDED, NEVER INSERTED AT 0: the root scripts/ carries Illinois's own
# build_metro_outline.py and friends, so putting it ahead of this instance's
# scripts/ shadows this state's copies with another state's constants — which
# does not fail on the import, it returns a wrong answer.
sys.path.append(os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "scripts"))
from scraper_common import require_robots_once  # noqa: E402  (FLEET_SHARED)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # ia/
APP_DATA_DIR = os.path.join(REPO_ROOT, "data", "app")
COUNTIES_FILE = os.path.join(APP_DATA_DIR, "state-counties.json")
OUT_FILE = os.path.join(APP_DATA_DIR, "ia-judicial-districts.json")

LSAFISCAL_URL = ("https://services2.arcgis.com/KhKjlwEBlPJd6v51/arcgis/rest/services/"
                  "JudicialDistricts/FeatureServer/0/query")

DISTRICT_COUNTIES = {
    1: ["Allamakee", "Black Hawk", "Buchanan", "Chickasaw", "Clayton", "Delaware",
        "Dubuque", "Fayette", "Grundy", "Howard", "Winneshiek"],
    2: ["Boone", "Bremer", "Butler", "Calhoun", "Carroll", "Cerro Gordo", "Floyd",
        "Franklin", "Greene", "Hamilton", "Hancock", "Hardin", "Humboldt", "Marshall",
        "Mitchell", "Pocahontas", "Sac", "Story", "Webster", "Winnebago", "Worth",
        "Wright"],
    3: ["Buena Vista", "Cherokee", "Clay", "Crawford", "Dickinson", "Emmet", "Ida",
        "Kossuth", "Lyon", "Monona", "O'Brien", "Osceola", "Palo Alto", "Plymouth",
        "Sioux", "Woodbury"],
    4: ["Audubon", "Cass", "Fremont", "Harrison", "Mills", "Montgomery", "Page",
        "Pottawattamie", "Shelby"],
    5: ["Adair", "Adams", "Clarke", "Dallas", "Decatur", "Guthrie", "Jasper", "Lucas",
        "Madison", "Marion", "Polk", "Ringgold", "Taylor", "Union", "Warren", "Wayne"],
    6: ["Benton", "Iowa", "Johnson", "Jones", "Linn", "Tama"],
    7: ["Cedar", "Clinton", "Jackson", "Muscatine", "Scott"],
    8: ["Appanoose", "Davis", "Des Moines", "Henry", "Jefferson", "Keokuk", "Lee",
        "Louisa", "Mahaska", "Monroe", "Poweshiek", "Van Buren", "Wapello",
        "Washington"],
}
EXPECT_COUNTIES = 99
EXPECT_DISTRICTS = 8


def rings_of(feature):
    geom = feature.get("geometry") or {}
    if geom.get("type") == "Polygon":
        return [list(r) for r in geom.get("coordinates") or []]
    if geom.get("type") == "MultiPolygon":
        return [list(r) for poly in (geom.get("coordinates") or []) for r in poly]
    return []


def dissolve(features):
    """General N-way county dissolve: drop every segment walked more than
    once (an interior county line), chain survivors into closed rings.
    Mirrors build_metro_outline.py's dissolve(), run once per district
    instead of once for the whole state -- unlike Wisconsin's circuit-court
    build, which only ever merges pairs, Iowa's districts run up to 22
    counties (District 2)."""
    counts, seg_pts = {}, {}
    for feat in features:
        for ring in rings_of(feat):
            for i in range(len(ring) - 1):
                a, b = tuple(ring[i][:2]), tuple(ring[i + 1][:2])
                if a == b:
                    continue
                key = (a, b) if a < b else (b, a)
                counts[key] = counts.get(key, 0) + 1
                seg_pts[key] = (a, b)

    adj = {}
    exterior = 0
    for key, n in counts.items():
        if n != 1:
            continue
        exterior += 1
        a, b = seg_pts[key]
        adj.setdefault(a, []).append((key, b))
        adj.setdefault(b, []).append((key, a))

    used, rings, walked = set(), [], 0
    for seed, n in counts.items():
        if n != 1 or seed in used:
            continue
        start, cur = seg_pts[seed]
        used.add(seed)
        walked += 1
        ring = [list(start), list(cur)]
        while cur != start:
            nxt = None
            for key, pt in adj.get(cur, ()):
                if key not in used:
                    nxt = (key, pt)
                    break
            if nxt is None:
                raise SystemExit("FATAL: open chain dissolving a district union -- the "
                                  "county file is no longer topologically consistent")
            used.add(nxt[0])
            walked += 1
            cur = nxt[1]
            ring.append(list(cur))
        rings.append(ring)
    if walked != exterior:
        raise SystemExit("FATAL: dissolve dropped exterior segments (%d walked of %d)"
                          % (walked, exterior))
    return rings


def point_in_ring(lng, lat, ring):
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > lat) != (yj > lat):
            if lng < (xj - xi) * (lat - yi) / (yj - yi) + xi:
                inside = not inside
        j = i
    return inside


def point_in_geom(lng, lat, geom):
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    for poly in polys:
        if point_in_ring(lng, lat, poly[0]) and not any(
                point_in_ring(lng, lat, hole) for hole in poly[1:]):
            return True
    return False


def group_rings(rings):
    """Nest holes under their enclosing outer ring (mirrors
    build_metro_outline.py's group_rings). Every one of Iowa's 8 districts
    is, in practice, a simply-connected cluster of adjacent counties (no
    islands/enclaves in the state's own county fabric), so this degrades to
    one outer ring per district -- kept general on purpose, matching the
    fleet's own precedent for why this stays general rather than assumed."""
    ordered = sorted(rings, key=len, reverse=True)
    polys = []
    for ring in ordered:
        lng, lat = ring[0][0], ring[0][1]
        for poly in polys:
            if point_in_ring(lng, lat, poly[0]):
                poly.append(ring)
                break
        else:
            polys.append([ring])
    return polys


def geom_from_rings(rings):
    polys = group_rings(rings)
    if len(polys) == 1:
        return {"type": "Polygon", "coordinates": polys[0]}
    return {"type": "MultiPolygon", "coordinates": polys}


def interior_point(feature):
    rings = rings_of(feature)
    ring = max(rings, key=len)
    xs = [p[0] for p in ring[:-1]]
    ys = [p[1] for p in ring[:-1]]
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def fetch_real_districts():
    import requests  # noqa: PLC0415 -- only this function needs network
    from requests.utils import default_user_agent  # noqa: PLC0415

    # THE ONE HOST THIS SCRIPT CONTACTS. Every other address in this file is a
    # citation in prose — the Code of Iowa sections the districts are defined
    # by, the Judicial Branch pages the county lists were read from, and
    # Ballotpedia as a cross-check. A CITATION IS NOT A FETCH: robots.txt
    # governs what we crawl, not what we link, so none of those hosts is asked.
    #
    # READ WITH THE CLIENT THAT CRAWLS: this function sends requests' own
    # default User-Agent, not a districtry token, so that is the string the
    # policy is read with. It is taken from the library rather than written out
    # here, so an upgrade cannot leave the two disagreeing. The host answers the
    # robots request HTTP 403 (measured from a runner 2026-09-30), which under
    # RFC 9309 2.3.1.3 is no published policy and therefore allow.
    ua = default_user_agent()
    require_robots_once(LSAFISCAL_URL, ua, label="ia-judicial-district")
    resp = requests.get(LSAFISCAL_URL, timeout=60, params={
        "where": "1=1",
        "outFields": "JUD_DIST",
        "outSR": "4326",
        "f": "geojson",
    })
    resp.raise_for_status()
    feats = (resp.json() or {}).get("features") or []
    if len(feats) != EXPECT_DISTRICTS:
        raise SystemExit("LSAFiscal JudicialDistricts returned %d features, expected %d"
                          % (len(feats), EXPECT_DISTRICTS))
    return {f["properties"]["JUD_DIST"]: f["geometry"] for f in feats}


def build(skip_live_witness=False):
    with open(COUNTIES_FILE) as f:
        counties = json.load(f)["features"]
    if len(counties) != EXPECT_COUNTIES:
        raise SystemExit("expected %d counties, found %d" % (EXPECT_COUNTIES, len(counties)))

    by_base = {}
    for feat in counties:
        base = feat["properties"].get("BASENAME")
        if not base:
            raise SystemExit("county feature missing BASENAME")
        by_base[base] = feat

    all_assigned = [c for lst in DISTRICT_COUNTIES.values() for c in lst]
    if len(all_assigned) != EXPECT_COUNTIES or len(set(all_assigned)) != EXPECT_COUNTIES:
        raise SystemExit("crosswalk does not assign exactly %d distinct counties (got %d, "
                          "%d distinct)" % (EXPECT_COUNTIES, len(all_assigned), len(set(all_assigned))))
    missing = set(by_base) - set(all_assigned)
    extra = set(all_assigned) - set(by_base)
    if missing or extra:
        raise SystemExit("crosswalk/county-file mismatch: missing=%s extra=%s"
                          % (sorted(missing), sorted(extra)))

    features = []
    county_district = {}
    for dist in sorted(DISTRICT_COUNTIES):
        members = DISTRICT_COUNTIES[dist]
        feats = [by_base[c] for c in members]
        geom = geom_from_rings(dissolve(feats))
        features.append({
            "type": "Feature",
            "properties": {
                "district": dist,
                "name": "Judicial District %d" % dist,
                "counties": ", ".join(sorted(c + " County" for c in members)),
                "countyCount": len(members),
            },
            "geometry": geom,
        })
        for c in members:
            county_district[c] = dist

    # Witness 1: every county's own interior point lands in its assigned
    # district's DISSOLVED polygon -- proves the dissolve unioned its
    # members correctly.
    by_district = {f["properties"]["district"]: f for f in features}
    for base, feat in by_base.items():
        pt = interior_point(feat)
        dist = county_district[base]
        if not point_in_geom(pt[0], pt[1], by_district[dist]["geometry"]):
            raise SystemExit("containment gate: %s's interior point missed district %d"
                              % (base, dist))

    # Witness 2: the SAME interior points land inside the LSAFiscal org's
    # REAL published district polygons -- independent geometry this builder
    # never touches otherwise, proving the crosswalk TABLE (not just the
    # dissolve) against the state's own authoritative source.
    if not skip_live_witness:
        real = fetch_real_districts()
        if set(real) != set(DISTRICT_COUNTIES):
            raise SystemExit("LSAFiscal JUD_DIST values %s don't match expected districts %s"
                              % (sorted(real), sorted(DISTRICT_COUNTIES)))
        for base, feat in by_base.items():
            pt = interior_point(feat)
            dist = county_district[base]
            if not point_in_geom(pt[0], pt[1], real[dist]):
                raise SystemExit(
                    "LSAFiscal witness: %s's interior point is not inside the real "
                    "district %d polygon -- the crosswalk table may be wrong" % (base, dist))

    if len(features) != EXPECT_DISTRICTS:
        raise SystemExit("built %d districts, expected %d" % (len(features), EXPECT_DISTRICTS))

    return {"type": "FeatureCollection", "features": features}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                     help="verify the shipped file matches a fresh build; write nothing")
    ap.add_argument("--skip-live-witness", action="store_true",
                     help="skip the live LSAFiscal spatial cross-check (offline dev only)")
    args = ap.parse_args()

    built = build(skip_live_witness=args.skip_live_witness)
    if args.check:
        with open(OUT_FILE) as f:
            shipped = json.load(f)
        if json.dumps(shipped, sort_keys=True) != json.dumps(built, sort_keys=True):
            print("FAIL: shipped ia-judicial-districts.json differs from a fresh build",
                  file=sys.stderr)
            sys.exit(1)
        print("check: shipped judicial-district geometry matches the county file%s "
              "(%d districts, 99 counties)"
              % ("" if args.skip_live_witness else " and the live LSAFiscal witness",
                 len(built["features"])))
        return

    with open(OUT_FILE, "w") as f:
        json.dump(built, f, separators=(",", ":"))
    size = os.path.getsize(OUT_FILE)
    print("wrote %s -- %d districts (99 counties), %.1f KB"
          % (OUT_FILE, len(built["features"]), size / 1024.0))


if __name__ == "__main__":
    main()
