#!/usr/bin/env python3
"""
Build the statewide judicial-district boundary file in data/app/ by
dissolving New York's 62 counties on the Judiciary Law section 140 lookup,
replacing the five-borough hand-applied crosswalk that shipped before PR 2.

What this replaces: ny/data/app/judicial-districts.json used to be the five
NYC counties relabeled 1, 2, 11, 12, 13, built by
ny/scripts/build_embedded_boundaries.py from a hand-applied crosswalk baked
into ny/data/judicial-districts.geojson (a file this script does not touch
and does not read). That crosswalk is retired by this file shipping; nothing
here deletes it, since deleting it is app-wiring, not this script's job.

New York Judiciary Law section 140 defines 13 judicial districts as unions of
whole counties. This script embeds the county-FIPS-to-district table as a
literal (COUNTY_DISTRICT below), and dissolves the state's county geometry on
it - read the shipped county fabric -> attach district -> dissolve -> validate
-> write data/app/judicial-districts.json. There is no simplify step, and that
is the whole of the 2026-09-26 change: see "Source for the county geometry"
below.

Provenance for COUNTY_DISTRICT: the statute text actually read on 2026-09-18
was https://newyork.public.law/laws/n.y._judiciary_law_section_140 (title
states "(2026)"; the page's own citation reads
"nysenate.gov/legislation/laws/JUD/140, updated Sep. 22, 2014, accessed Sep.
12, 2026"). Four other candidate hosts were tried the same day and none was
read: law.justia.com, www.nysenate.gov and www.nycourts.gov/ww2.nycourts.gov
each answered a Cloudflare managed challenge to this client (recorded here as
BLOCKED, not as absent - a challenge is an access control and this project
never solves or works around one); public.leginfo.state.ny.us (the NY
Assembly's own "Laws" search) answered a connection reset (unreachable).
Cross-checked the same day against
https://en.wikipedia.org/wiki/Supreme_Court_of_the_State_of_New_York, which
independently enumerates the same 13 districts over the same 62 counties,
county for county, differing only in writing "St. Lawrence" where the statute
text writes "Saint Lawrence."

The trap this table exists to survive: the statute spells one county "Saint
Lawrence," and the NYS_Civil_Boundaries layer's own NAME field spells the same
county "St Lawrence" (no period, FIPS 36089). The join below is keyed on
FIPS_CODE, never on name, for exactly this reason - a name-keyed join would
either silently drop St Lawrence or require the alias to be maintained by
hand. This script also checks the layer's NAME field against the table's own
county_name_by_fips at build time and refuses to write if any of the 62 no
longer match, because a name drift the join itself cannot see is a change
this project has not verified.

Source for the county geometry: data/app/ny-counties.json, the file
ny/scripts/build_ny_civil_boundaries.py writes. THIS SCRIPT USED TO DO ITS OWN
FETCH OF NYS_Civil_Boundaries/FeatureServer/2 AND SIMPLIFY IT AGAIN AT 15%, and
that was the defect: a judicial district is a union of WHOLE COUNTIES, so its
boundary is made of county lines, and simplifying the same source twice in two
mapshaper runs cannot produce the same line twice. Measured 2026-09-26 on the
shipped files, 99.98% of judicial vertices were still also county vertices and
the two disagreed by up to 11.2 m - small, because both runs used identical
settings on identical input, and pure luck rather than a property of the
pipeline. Reading the shipped county fabric and dissolving it with NO further
simplification makes the nesting exact by construction: a judicial boundary is
literally a union of the arcs that ship in ny-counties.json, and
check_vertices_are_county_vertices() below refuses the build if a single vertex
is not one. It also retires a duplicate 4 MB fetch of a layer the sibling
builder already reads, which that builder's own docstring had been complaining
about since 2026-09-18.

THE COST IS A BUILD-ORDER DEPENDENCY AND IT IS STATED RATHER THAN HIDDEN: this
script now reads a built file, so ny-counties.json must be rebuilt first and
this file rebuilt in the same change. ny/scripts/validate_index.py fails the
merge gate if the two files stop sharing vertices, which is what makes the
dependency enforced rather than remembered. The shoreline-clip / EPSG:26918
trap is unchanged and is recorded in build_ny_civil_boundaries.py's docstring.

Dissolve: mapshaper's -dissolve merges the county polygons sharing a district
number into one feature per district and drops the internal county-to-county
edges, which is what "unions of whole counties" means as geometry - a
district made of several counties should render as one region, not as its
component counties glued together with visible seams. THERE IS NO
SIMPLIFICATION STEP: the county geometry this reads is already simplified, and
simplifying a dissolve of it again is what put the two layers' lines up to
11.2 m apart. mapshaper is still pinned to mapshaper@0.6.102, for the dissolve.
Validation re-classifies 2,000 random points across the measured state envelope
against BOTH the county-to-district mapping and the dissolved result, and
refuses to write on disagreement or on any point landing in two districts. That
now checks the DISSOLVE alone, which is all there is left to check here -
whether the geometry itself is faithful to the publisher is
build_ny_civil_boundaries.py's gate, on the file this reads.

Card: no roster. A New York Supreme Court justice is elected countywide (or,
for the 5th and 8th districts' at-large seats, district-wide) to a 14-year
term; there is no clean machine-readable per-district roster, so the card
links to nycourts.gov rather than guessing a name.

Prerequisites: Node.js (mapshaper via `npx mapshaper@<pinned>`) and a built
data/app/ny-counties.json. No network.

Usage:
    python3 ny/scripts/build_ny_civil_boundaries.py     # first: writes ny-counties.json
    python3 ny/scripts/build_ny_judicial_districts.py
"""

import json
import os
import random
import subprocess
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DATA_DIR = os.path.join(REPO_ROOT, "data", "app")
MAPSHAPER = "mapshaper@0.6.102"  # pinned for reproducible output (fleet convention)
COUNTIES_FILE = os.path.join(APP_DATA_DIR, "ny-counties.json")

OUT_FILE = "judicial-districts.json"
# NO RAW SOURCE SNAPSHOT IS WRITTEN, and that is a decision rather than an
# omission. The first version of this builder wrote the whole 4.3 MB fetch to
# data/source/ on every run. Measured 2026-09-18: this builder and
# build_ny_judicial_districts.py fetch the SAME county layer, so the two
# snapshots were 8.6 MB of near-identical geometry, against 1.5 MB for all of
# Wisconsin's build inputs put together. Nothing read either file back. The
# builder's guards are what make a run reproducible: it refuses to write
# unless the source still returns exactly what it expects, and the source is a
# public service this project can re-fetch. ny/scripts/build_ny_school_districts.py
# and ny/scripts/build_ny_civil_boundaries.py made the same call for the same
# reason. Since 2026-09-26 this builder fetches nothing at all.
PRECISION = "0.000001"  # 6 decimals ~= 0.11 m, the precision the app requests live
EXPECTED_COUNTIES = 62
EXPECTED_DISTRICTS = 13

# New York Judiciary Law section 140, as read 2026-09-18 (statute source and
# blocked-host record in the module docstring above). Key is the ArcGIS
# layer's own FIPS_CODE string; value is the judicial district number.
# The name each FIPS is expected to carry on the layer's NAME field is
# checked at build time against COUNTY_NAME_BY_FIPS below, never assumed.
COUNTY_DISTRICT = {
    "36061": 1,
    "36047": 2,
    "36021": 3, "36105": 3, "36111": 3, "36039": 3, "36001": 3, "36095": 3, "36083": 3,
    "36113": 4, "36091": 4, "36115": 4, "36031": 4, "36033": 4, "36089": 4, "36019": 4,
    "36057": 4, "36041": 4, "36035": 4, "36093": 4,
    "36067": 5, "36065": 5, "36075": 5, "36043": 5, "36045": 5, "36049": 5,
    "36077": 6, "36025": 6, "36053": 6, "36017": 6, "36007": 6, "36107": 6, "36015": 6,
    "36109": 6, "36023": 6, "36097": 6,
    "36051": 7, "36117": 7, "36099": 7, "36123": 7, "36069": 7, "36101": 7, "36055": 7,
    "36011": 7,
    "36029": 8, "36013": 8, "36009": 8, "36073": 8, "36063": 8, "36037": 8, "36003": 8,
    "36121": 8,
    "36119": 9, "36079": 9, "36027": 9, "36071": 9, "36087": 9,
    "36059": 10, "36103": 10,
    "36081": 11,
    "36005": 12,
    "36085": 13,
}

# The name the layer's own NAME field is expected to carry for each FIPS,
# read from the same statute pass. "St Lawrence" (no period) is the layer's
# spelling for the county the statute text spells "Saint Lawrence" - the one
# documented alias; every other name matches exactly, same case and
# punctuation.
COUNTY_NAME_BY_FIPS = {
    "36061": "New York", "36047": "Kings", "36021": "Columbia", "36105": "Sullivan",
    "36111": "Ulster", "36039": "Greene", "36001": "Albany", "36095": "Schoharie",
    "36083": "Rensselaer", "36113": "Warren", "36091": "Saratoga", "36115": "Washington",
    "36031": "Essex", "36033": "Franklin", "36089": "St Lawrence", "36019": "Clinton",
    "36057": "Montgomery", "36041": "Hamilton", "36035": "Fulton", "36093": "Schenectady",
    "36067": "Onondaga", "36065": "Oneida", "36075": "Oswego", "36043": "Herkimer",
    "36045": "Jefferson", "36049": "Lewis", "36077": "Otsego", "36025": "Delaware",
    "36053": "Madison", "36017": "Chenango", "36007": "Broome", "36107": "Tioga",
    "36015": "Chemung", "36109": "Tompkins", "36023": "Cortland", "36097": "Schuyler",
    "36051": "Livingston", "36117": "Wayne", "36099": "Seneca", "36123": "Yates",
    "36069": "Ontario", "36101": "Steuben", "36055": "Monroe", "36011": "Cayuga",
    "36029": "Erie", "36013": "Chautauqua", "36009": "Cattaraugus", "36073": "Orleans",
    "36063": "Niagara", "36037": "Genesee", "36003": "Allegany", "36121": "Wyoming",
    "36119": "Westchester", "36079": "Putnam", "36027": "Dutchess", "36071": "Orange",
    "36087": "Rockland", "36059": "Nassau", "36103": "Suffolk", "36081": "Queens",
    "36005": "Bronx", "36085": "Richmond",
}

# The five boroughs, as FIPS -> the district the CURRENT shipped file (the
# five-borough crosswalk this build replaces) puts them in. Read from
# ny/data/app/judicial-districts.json before it is overwritten; the new
# lookup must place every one of these the same way, or something about the
# five-borough baseline has changed underneath this build.
BOROUGH_DISTRICT_BASELINE = {
    "36061": 1,   # New York (Manhattan)
    "36047": 2,   # Kings (Brooklyn)
    "36081": 11,  # Queens
    "36005": 12,  # Bronx
    "36085": 13,  # Richmond (Staten Island)
}


def read_shipped_counties():
    """Read the county fabric ny/scripts/build_ny_civil_boundaries.py writes.

    A judicial district is a union of WHOLE counties, so its boundary is made of
    county lines; dissolving the SHIPPED county geometry is what makes the two
    layers' lines the same line rather than two drawings of one. See the module
    docstring for the 11.2 m disagreement this replaced."""
    if not os.path.exists(COUNTIES_FILE):
        raise RuntimeError(
            "judicial-districts: data/app/ny-counties.json is not there. Run "
            "`python3 ny/scripts/build_ny_civil_boundaries.py` first -- this "
            "builder dissolves that file and no longer fetches the county layer."
        )
    with open(COUNTIES_FILE) as fh:
        geo = json.load(fh)
    feats = geo.get("features") or []
    if not feats:
        raise RuntimeError("judicial-districts: data/app/ny-counties.json carries no features")
    return geo


def county_vertices(features):
    """Every vertex of a set of features, as a set of (lng, lat) pairs."""
    out = set()
    for f in features:
        geom = f.get("geometry")
        if not geom:
            continue

        def walk(c):
            if c and isinstance(c[0], (int, float)):
                out.add((c[0], c[1]))
            else:
                for x in c:
                    walk(x)

        walk(geom["coordinates"])
    return out


def check_vertices_are_county_vertices(result_feats, county_feats):
    """EVERY judicial vertex must be a county vertex, with no tolerance.

    This is the gate the whole 2026-09-26 change is for. A district assembled
    from county arcs and simplified no further can only be made of the counties'
    own vertices; a single vertex that is not one means something re-derived the
    geometry, and the two layers will draw one line twice. Measured on the files
    this replaced: 6,207 of 6,208, i.e. it failed by one vertex."""
    cv = county_vertices(county_feats)
    jv = county_vertices(result_feats)
    stray = jv - cv
    if stray:
        raise RuntimeError(
            "judicial-districts: %d of %d vertices are not vertices of "
            "data/app/ny-counties.json (e.g. %r) -- the dissolve must be of the "
            "SHIPPED county geometry with no further simplification. Refusing to write."
            % (len(stray), len(jv), sorted(stray)[:3])
        )
    return len(jv), len(cv)


def read_current_shipped_baseline(path):
    """Read the file this build is about to overwrite and, IF it is the old
    five-borough file, check it still carries the placement this build's
    baseline expects.

    THE CHECK ONLY APPLIES TO THE OLD SHAPE, AND THAT IS THE POINT. The file
    this replaces was five county polygons relabelled 1, 2, 11, 12 and 13 by
    a hand-applied crosswalk, keyed `countyfips`. This build writes 13
    statewide districts keyed `district` and `county_fips`, so once it has run
    once the old keys are gone. Reading the new shape and demanding the old
    one made the builder refuse to run a second time, which is not a guard,
    it is a builder that works once. Measured on 2026-09-18: the first run
    succeeded and the second failed with all five boroughs reported missing.

    The borough placement is still checked on every run, against the OUTPUT
    rather than against whatever happens to be on disk: see
    check_borough_placement(), which reads this build's own dissolved result.
    That is the durable form of the same question, because the statute is the
    authority and the shipped file is not."""
    if not os.path.exists(path):
        print("judicial-districts: no existing file at %s - skipping baseline check" % path, file=sys.stderr)
        return
    with open(path) as f:
        current = json.load(f)
    by_fips = {}
    for feat in current.get("features", []):
        props = feat.get("properties", {})
        fips = props.get("countyfips")
        if fips is not None:
            by_fips[str(fips)] = props.get("district")
    if not by_fips:
        # Not the old five-borough shape: this build has already run here, or
        # the file came from somewhere else. Nothing to compare, and the
        # output check below is what actually holds the placement.
        print("judicial-districts: existing file is not the five-borough shape "
              "- nothing to baseline against, the output check still applies",
              file=sys.stderr)
        return
    mismatches = []
    for fips, expected in BOROUGH_DISTRICT_BASELINE.items():
        actual = by_fips.get(fips)
        if actual != expected:
            mismatches.append((fips, expected, actual))
    if mismatches:
        raise RuntimeError(
            "judicial-districts: the currently shipped file disagrees with "
            "this build's five-borough baseline (fips, expected, found in "
            "shipped file): %s - refusing to write" % mismatches
        )


def run_mapshaper_dissolve(source_path, out_path):
    """Dissolve only. NO -simplify: the input is already the shipped county
    geometry, and simplifying a dissolve of it again is the defect this builder
    retired on 2026-09-26 (module docstring)."""
    subprocess.run(
        [
            "npx", "-y", MAPSHAPER, source_path,
            "-dissolve", "district",
            "calc=counties=collect(county);county_fips=collect(county_fips)",
            "-o", "precision=" + PRECISION, "format=geojson", out_path,
        ],
        check=True, cwd=REPO_ROOT,
    )


# --- point-in-polygon mirroring index.html's even-odd test (so validation
#     agrees with what the app computes at runtime) - fleet-standard copy ---
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
    return [(f["properties"].get(key_prop), f["geometry"], _bbox(f["geometry"])) for f in features]


def _districts_at(model, pt):
    hits = []
    for key, geom, bb in model:
        if bb[0] <= pt[0] <= bb[2] and bb[1] <= pt[1] <= bb[3] and _point_in_geometry(pt, geom):
            hits.append(key)
    return hits


def _state_bbox(features):
    """Measure the state envelope from the fetched geometry itself, so
    validation samples the extent this build actually saw."""
    b = [1e9, 1e9, -1e9, -1e9]
    for f in features:
        fb = _bbox(f["geometry"])
        b[0], b[1] = min(b[0], fb[0]), min(b[1], fb[1])
        b[2], b[3] = max(b[2], fb[2]), max(b[3], fb[3])
    return {"minLng": b[0], "minLat": b[1], "maxLng": b[2], "maxLat": b[3]}


def validate(source_with_district, result_features, samples=2000, seed=2024):
    """Refuse the build unless the DISSOLVE preserves district classification
    over the state envelope vs. classifying the counties directly through
    COUNTY_DISTRICT - the fleet's 2,000 uniform-random-point protocol. Any point
    landing in two result districts is a topology break.

    ITS SUBJECT NARROWED ON 2026-09-26 and this docstring says so rather than
    keeping a claim that had stopped being true: it used to say it checked "the
    whole pipeline (dissolve AND simplify)", and there is no simplify step here
    any more. Whether the geometry is faithful to the publisher is
    build_ny_civil_boundaries.py's gate, on the very file this dissolves."""
    state_bbox = _state_bbox(source_with_district)
    src = _model(source_with_district, "district")
    new = _model(result_features, "district")
    rng = random.Random(seed)
    agree = overlaps = 0
    for _ in range(samples):
        pt = (rng.uniform(state_bbox["minLng"], state_bbox["maxLng"]),
              rng.uniform(state_bbox["minLat"], state_bbox["maxLat"]))
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
        return False, "topology broken: %d/%d points fell in >1 district" % (overlaps, samples), state_bbox
    if pct < 99.5:
        return False, "point-in-district agreement only %.2f%% (need >= 99.5%%)" % pct, state_bbox
    return True, "%d/%d (%.2f%%) agreement over the measured state envelope, 0 overlaps" % (agree, samples, pct), state_bbox


def check_borough_placement(result_feats):
    """Assert the five boroughs came out where Judiciary Law S140 puts them.

    This is the durable form of the five-borough guard: it reads THIS BUILD'S
    OWN dissolved output rather than whatever file happens to be on disk, so
    it holds on every run instead of only the first one. The five values are
    also what the app shipped before this layer went statewide, so a change
    here would move ground a reader already sees."""
    by_fips = {}
    for feat in result_feats:
        d = feat["properties"]["district"]
        for fips in feat["properties"]["county_fips"]:
            by_fips[str(fips)] = d
    mismatches = []
    for fips, expected in BOROUGH_DISTRICT_BASELINE.items():
        actual = by_fips.get(fips)
        if actual != expected:
            mismatches.append((fips, expected, actual))
    if mismatches:
        raise RuntimeError(
            "judicial-districts: the BUILT districts put a borough somewhere "
            "the statute table does not (fips, expected, built): %s "
            "- refusing to write" % mismatches
        )


def main():
    out_path = os.path.join(APP_DATA_DIR, OUT_FILE)
    old_size = os.path.getsize(out_path) if os.path.exists(out_path) else None
    read_current_shipped_baseline(out_path)

    if set(COUNTY_DISTRICT) != set(COUNTY_NAME_BY_FIPS):
        raise RuntimeError(
            "judicial-districts: COUNTY_DISTRICT and COUNTY_NAME_BY_FIPS carry "
            "different FIPS sets - table is internally inconsistent, refusing to write"
        )
    if len(COUNTY_DISTRICT) != EXPECTED_COUNTIES:
        raise RuntimeError(
            "judicial-districts: embedded lookup carries %d counties (expected "
            "exactly %d) - refusing to write" % (len(COUNTY_DISTRICT), EXPECTED_COUNTIES)
        )
    lookup_districts = set(COUNTY_DISTRICT.values())
    if lookup_districts != set(range(1, EXPECTED_DISTRICTS + 1)):
        raise RuntimeError(
            "judicial-districts: embedded lookup's district numbers are %s "
            "(expected exactly 1..%d) - refusing to write"
            % (sorted(lookup_districts), EXPECTED_DISTRICTS)
        )

    source = read_shipped_counties()
    feats = source["features"]

    n = len(feats)
    if n != EXPECTED_COUNTIES:
        raise RuntimeError(
            "judicial-districts: %d counties fetched (expected exactly %d) "
            "- refusing to write" % (n, EXPECTED_COUNTIES)
        )

    layer_fips = set(f["properties"]["FIPS_CODE"] for f in feats)
    lookup_fips = set(COUNTY_DISTRICT)
    if layer_fips != lookup_fips:
        raise RuntimeError(
            "judicial-districts: the layer's FIPS_CODE set no longer matches "
            "the embedded Judiciary Law S140 table (layer-only: %s, "
            "table-only: %s) - refusing to write"
            % (sorted(layer_fips - lookup_fips), sorted(lookup_fips - layer_fips))
        )

    name_mismatches = [
        (f["properties"]["FIPS_CODE"], f["properties"]["NAME"], COUNTY_NAME_BY_FIPS[f["properties"]["FIPS_CODE"]])
        for f in feats
        if f["properties"]["NAME"] != COUNTY_NAME_BY_FIPS[f["properties"]["FIPS_CODE"]]
    ]
    if name_mismatches:
        raise RuntimeError(
            "judicial-districts: the layer's NAME field no longer matches "
            "the embedded table (fips, layer name, table name): %s - "
            "refusing to write" % name_mismatches
        )

    # Sort counties alphabetically within each district before the dissolve,
    # so collect(county) (which preserves input order) produces an
    # alphabetically sorted counties list without depending on mapshaper's
    # expression language to sort (it has no working .sort() on collect()'s
    # result, measured 2026-09-18).
    feats_sorted = sorted(feats, key=lambda f: f["properties"]["NAME"])

    source_with_district = []
    for f in feats_sorted:
        fips = f["properties"]["FIPS_CODE"]
        district = COUNTY_DISTRICT[fips]
        source_with_district.append({
            "type": "Feature",
            "properties": {
                "district": district,
                "county": f["properties"]["NAME"],
                "county_fips": fips,
            },
            "geometry": f["geometry"],
        })

    expected_counts = {}
    for d in COUNTY_DISTRICT.values():
        expected_counts[d] = expected_counts.get(d, 0) + 1

    with tempfile.TemporaryDirectory() as tmp:
        src_path = os.path.join(tmp, "counties-with-district.geojson")
        with open(src_path, "w") as f:
            json.dump({"type": "FeatureCollection", "features": source_with_district}, f)
        out_tmp = os.path.join(tmp, "judicial-districts.geojson")
        run_mapshaper_dissolve(src_path, out_tmp)
        with open(out_tmp) as f:
            dissolved = json.load(f)

    result_feats = dissolved["features"]
    if len(result_feats) != EXPECTED_DISTRICTS:
        raise RuntimeError(
            "judicial-districts: dissolve produced %d districts (expected "
            "exactly %d) - refusing to write" % (len(result_feats), EXPECTED_DISTRICTS)
        )

    seen_districts = set()
    for rf in result_feats:
        d = rf["properties"]["district"]
        counties = rf["properties"].get("counties") or []
        if not counties:
            raise RuntimeError("judicial-districts: district %s has no counties after dissolve - refusing to write" % d)
        if len(counties) != expected_counts.get(d):
            raise RuntimeError(
                "judicial-districts: district %s carries %d counties after "
                "dissolve, table expects %d - refusing to write"
                % (d, len(counties), expected_counts.get(d))
            )
        seen_districts.add(d)
        rf["properties"]["num_counties"] = len(counties)
        # The card's field renderer prints a property as it finds it, and a raw
        # array prints as "Albany,Columbia,Greene" with no spaces. Join it here
        # so the display string is data rather than something the app has to
        # format; `counties` stays on the feature for any other reader.
        rf["properties"]["counties_label"] = ", ".join(counties)
    if seen_districts != set(range(1, EXPECTED_DISTRICTS + 1)):
        raise RuntimeError(
            "judicial-districts: districts present after dissolve are %s "
            "(expected exactly 1..%d) - refusing to write"
            % (sorted(seen_districts), EXPECTED_DISTRICTS)
        )

    # The five-borough placement must hold in the freshly built result too,
    # not only in the file being replaced.
    result_by_district = {rf["properties"]["district"]: rf["properties"]["counties"] for rf in result_feats}
    for fips, expected_district in BOROUGH_DISTRICT_BASELINE.items():
        county_name = COUNTY_NAME_BY_FIPS[fips]
        if county_name not in result_by_district.get(expected_district, []):
            raise RuntimeError(
                "judicial-districts: %s (fips %s) is not in built district %d "
                "- refusing to write" % (county_name, fips, expected_district)
            )

    ok, msg, state_bbox = validate(source_with_district, result_feats)
    if not ok:
        raise RuntimeError("judicial-districts validation failed: %s" % msg)

    check_borough_placement(result_feats)

    # The nesting gate: every vertex of every district must be a vertex of the
    # county fabric it was dissolved from. Exact, no tolerance -- see the
    # function's own docstring for why that is available here at all.
    n_jud_verts, n_county_verts = check_vertices_are_county_vertices(result_feats, feats)


    compact = json.dumps(dissolved, separators=(",", ":"))
    if json.loads(compact) != dissolved:
        raise RuntimeError("judicial-districts round-trip mismatch before writing")

    os.makedirs(APP_DATA_DIR, exist_ok=True)
    with open(out_path, "w") as f:
        f.write(compact)
    new_size = len(compact)

    print(
        "judicial-districts -> data/app/%s: %d districts over %d counties "
        "(statewide, computed); state envelope measured lng %.3f..%.3f lat "
        "%.3f..%.3f; %s; %d bytes (dissolve only, no simplify, %s precision); "
        "all %d vertices are among ny-counties.json's %d; the file it "
        "replaced on the day this shipped was the 15,948-byte five-borough "
        "crosswalk (measured 2026-09-18 on origin/main). %s"
        % (OUT_FILE, len(result_feats), EXPECTED_COUNTIES, state_bbox["minLng"],
           state_bbox["maxLng"], state_bbox["minLat"], state_bbox["maxLat"],
           msg, new_size, PRECISION, n_jud_verts, n_county_verts,
           ("Previous file on disk: %d bytes." % old_size) if old_size is not None
           else "No prior file on disk."),
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
