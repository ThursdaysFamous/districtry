"""
Shared machinery for counties whose board districts are UNIONS OF WHOLE
PRECINCTS and whose precinct fabric is still the Census 2020 voting-district
fabric — the "canvass route" of docs/EXPANSION_GUIDE.md §3.5.1.

WHY THIS MODULE EXISTS. Clark shipped the route on 2026-08-18 with every step
inline in scripts/build_clark_boundaries.py. The 34-county sweep of the
`pollresults.net` / `accessliberty.com` vendor pair that same day found the
route applies to several more counties unchanged, and three copies of a
dissolve is how two of them quietly drift apart. So the parts that are
genuinely identical live here: fetch the county's Census 2020 VTDs, check them
against the county's own precinct list (THE JASPER TEST), dissolve them per a
composition, prove the result tiles the county, and emit the two GeoJSON files
the app reads. Everything county-specific — the composition itself, the
witnesses that establish it, the counts and the prose — stays in the county's
own builder, which is where a reader looks for it.

(build_clark_boundaries.py predates this module and still carries its own copy.
It is deliberately not migrated in the same change that introduced this file:
Clark had merged hours earlier and a refactor of a just-shipped county buys
risk, not safety. Migrating it is a clean follow-up, and its --check is a byte
compare, so the migration is provable.)

THE JASPER TEST, which is the whole gate. Census VTDs are the county's
precincts AS OF JANUARY 2020, not necessarily today. Jasper carries five
census Wade voting districts where the county now runs four precincts, so its
fabric moved and no dissolve of census geometry could answer for the county
seat. `check_fabric` refuses to continue unless the census names match the
county's current precinct names one-for-one AND the VTD populations sum to the
county's own Census 2020 count. A county that fails is not buildable this way,
and the failure says so in those words.
"""

import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import requests  # noqa: E402
from build_metro_outline import HEADERS, REQUEST_TIMEOUT, STATE_FIPS  # noqa: E402
from scraper_common import require_robots_once  # noqa: E402  (FLEET_SHARED)

VTD_URL = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
           "tigerWMS_Census2020/MapServer/58/query")
COUNTY2020_URL = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                  "tigerWMS_Census2020/MapServer/82/query")
COORD_PRECISION = 6


def norm(name):
    """Compare precinct names the way two publishers spell them, not byte for
    byte: case, punctuation and spacing differ freely between a county's
    results feed and the census BASENAME (CLAY CITY vs CLAY CITY I is a REAL
    difference and stays one; "Robinson  1" vs "ROBINSON 1" is not)."""
    return re.sub(r"[^A-Z0-9]", "", (name or "").upper())


# Roman numerals a precinct ordinal can plausibly be, and NOTHING WIDER. The
# obvious rule — "uppercase any token that is a valid roman numeral" — mangles
# real place names: DIX is a village in Jefferson County and a valid 509, MI is
# a valid 1001, CIVIL parses as a numeral too. Restricting the alphabet to I, V
# and X and the length to four keeps every ordinal a county actually uses (I
# through XXXIX) and excludes all three of those.
_ROMAN_ORDINAL = re.compile(r"^(X{0,3})(IX|IV|V?I{0,3})$")


def _cap_word(word):
    if word.isdigit():
        return word
    if word and len(word) <= 4 and _ROMAN_ORDINAL.match(word.upper()):
        return word.upper()
    return word.capitalize()


def title_case(name):
    """Display form for an ALL-CAPS census BASENAME.

    Two cases the plain str.capitalize() gets wrong, both found in Scott County
    on 2026-08-21 and both visible on a card: a HYPHENATED name lowercases its
    second half (EXETER-BLUFFS became "Exeter-bluffs"), and a ROMAN NUMERAL
    becomes a word (WINCHESTER III became "Winchester Iii"). Apostrophes are
    deliberately NOT special-cased — O'FALLON would want "O'Fallon" and WRIGHT'S
    would want "Wright's", and no rule gets both — so a county with one needs an
    explicit label rather than this function."""
    out = []
    for word in str(name).split():
        out.append("-".join(_cap_word(part) for part in word.split("-")))
    return " ".join(out)


def get_json(url, params, fail):
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-vtd-board-districts")
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, params=params)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and data.get("error"):
        fail("%s answered an error: %s" % (url, data["error"]))
    return data


def fetch_vtds(county_fips, shape_fn, fail):
    """{normalised name: {geom, geoid, pop, basename}} for one county."""
    data = get_json(VTD_URL, {
        "where": "STATE='%s' AND COUNTY='%s'" % (STATE_FIPS, county_fips),
        "outFields": "GEOID,BASENAME,POP100", "returnGeometry": "true",
        "outSR": "4326", "f": "geojson"}, fail)
    out = {}
    for feature in data.get("features") or []:
        props = feature.get("properties") or {}
        base = " ".join((props.get("BASENAME") or "").upper().split())
        key = norm(base)
        if key in out:
            fail("the census voting-district layer carries two features named %r" % base)
        geom = shape_fn(feature["geometry"])
        out[key] = {"geom": geom if geom.is_valid else geom.buffer(0),
                    "geoid": props.get("GEOID"), "pop": int(props.get("POP100") or 0),
                    "basename": base}
    return out


def fetch_county(county_fips, shape_fn, fail):
    data = get_json(COUNTY2020_URL, {
        "where": "STATE='%s' AND COUNTY='%s'" % (STATE_FIPS, county_fips),
        "outFields": "POP100", "returnGeometry": "true", "outSR": "4326",
        "f": "geojson"}, fail)
    feats = data.get("features") or []
    if not feats:
        fail("Census 2020 county layer returned nothing for county %s" % county_fips)
    return shape_fn(feats[0]["geometry"]), int((feats[0].get("properties") or {}).get("POP100") or 0)


def apply_aliases(vtds, aliases, fail):
    """Re-key census VTDs onto the COUNTY'S spelling where the two publishers
    differ. `aliases` maps county name -> census BASENAME.

    This is a rename, never a merge, and the guards say so: each alias must
    name a census feature that exists and a county name that does not already
    have one, and no two aliases may point at the same feature. Edgar is the
    case it was written for — the census writes EMBARRASS 1 and KANSAS 1 where
    the county writes Embarrass and Kansas, 29 of its 31 names match exactly,
    and the remaining two therefore pair uniquely with nothing to choose
    between. A county needing an alias for a name that is genuinely ambiguous
    is a county this route cannot serve."""
    for county_name, census_name in (aliases or {}).items():
        ck, xk = norm(county_name), norm(census_name)
        if xk not in vtds:
            fail("alias %r -> %r names a census feature that does not exist"
                 % (county_name, census_name))
        if ck in vtds:
            fail("alias %r -> %r would overwrite a census feature that already "
                 "carries the county's spelling" % (county_name, census_name))
        rec = vtds.pop(xk)
        rec["censusName"] = rec["basename"]
        rec["basename"] = " ".join(str(county_name).upper().split())
        vtds[ck] = rec
    return vtds


def check_fabric(vtds, county_precincts, county_pop, fail):
    """THE JASPER TEST. `county_precincts` is the county's own current precinct
    list, as its election authority publishes it.

    A FAILURE HERE IS A HYPOTHESIS, NOT A VERDICT. Measured across the frontier
    on 2026-08-20, ten counties in one sweep were rejected by this comparison
    for reasons that are not a moved fabric at all — census truncation at 17
    characters, zero-padding, a vestigial trailing 1/I, ISBE reporting-unit
    suffixes, and (added 2026-09-04) roman ordinals written arabic plus a
    spelled-out PCT/TWP unit word. Each runs in EITHER direction. Before
    recording a county as re-precincted, run
    `python3 scripts/isbe_precinct_fabric.py --jasper <election> --county <name>`,
    which applies all six with their guards and prints which one it ruled out;
    what survives is either a real fabric change or a spelling, and the two need
    different work — a spelling is what `apply_aliases` above is for."""
    want = {norm(p) for p in county_precincts}
    have = set(vtds)
    if want != have:
        only_county = sorted(want - have)
        only_census = sorted(have - want)
        fail("the Census 2020 voting-district fabric is NOT this county's current "
             "precinct fabric — county-only %s; census-only %s. The county "
             "re-precincted after the 2020 census, so no dissolve of census "
             "geometry can answer for it (this is the test Jasper fails)."
             % (only_county or "none", only_census or "none"))
    vtd_pop = sum(v["pop"] for v in vtds.values())
    if vtd_pop != county_pop:
        fail("the %d voting districts sum to %d people and the county to %d — the "
             "fabric is not a tiling of the county" % (len(vtds), vtd_pop, county_pop))
    return vtd_pop


def check_fabric_composed(vtds, county_pop, fail):
    """THE JASPER TEST for a county whose precincts are unions of WHOLE VTDs.

    check_fabric above compares the county's precinct NAMES against the census
    VTD names one-for-one, which is exactly right for the Clark shape — one
    precinct per voting district — and exactly wrong for the shape Calhoun has.
    Calhoun runs five precincts over seven census voting districts, and it says
    so in their names: Belleview-Hamburg is BELLEVIEW plus HAMBURG, Hardin-Gilead
    is HARDIN plus GILEAD. Demanding name equality there rejects a county whose
    fabric has not moved at all.

    What survives is the half that actually tests the fabric: the voting
    districts must still TILE the county, which the population identity proves.
    The other half of check_fabric's job — that the composition accounts for
    every voting district exactly once, with none left over and none claimed
    twice — is already check_partition's, so a composed county gets the same
    coverage from the pair that a one-to-one county gets from check_fabric
    alone. Nothing is relaxed; the test is split across two calls instead of
    one.

    THE FAILURE THIS DOES NOT CATCH, said plainly because the population sum
    passing is seductive: a county that re-precincted after 2020 can still sum
    to its own Census 2020 count exactly — Bond, Jersey and Jo Daviess all do.
    The sum says the fabric tiled the county in 2020, never that it is the
    county's fabric today. For a composed county that assurance has to come
    from the composition itself being witnessed in the county's own certified
    returns, which is the caller's job and belongs in the caller's docstring.
    """
    vtd_pop = sum(v["pop"] for v in vtds.values())
    if vtd_pop != county_pop:
        fail("the %d voting districts sum to %d people and the county to %d — the "
             "fabric is not a tiling of the county" % (len(vtds), vtd_pop, county_pop))
    return vtd_pop


def check_partition(composition, vtds, fail):
    """Every precinct in exactly one district, and every precinct used."""
    seen = {}
    for dnum, names in composition.items():
        for name in names:
            key = norm(name)
            if key not in vtds:
                fail("district %s claims precinct %r, which the census fabric does "
                     "not carry" % (dnum, name))
            if key in seen:
                fail("precinct %r is claimed by districts %s and %s — this county "
                     "SPLITS precincts between districts, so its boundary cannot be "
                     "a dissolve of whole precincts (the Jasper/Wade shape)"
                     % (name, seen[key], dnum))
            seen[key] = dnum
    unclaimed = sorted(vtds[k]["basename"] for k in set(vtds) - set(seen))
    if unclaimed:
        fail("no district claims %s — the composition is incomplete"
             % ", ".join(unclaimed))
    return seen


def dissolve(composition, vtds, unary_union):
    districts, pops = {}, {}
    for dnum, names in composition.items():
        merged = unary_union([vtds[norm(n)]["geom"] for n in names])
        districts[dnum] = merged if merged.is_valid else merged.buffer(0)
        pops[dnum] = sum(vtds[norm(n)]["pop"] for n in names)
    return districts, pops


def check_tiling(districts, county_geom, transform, max_overlap_m2, min_covered,
                 unary_union, fail):
    lat = county_geom.centroid.y
    mx, my = 111320.0 * math.cos(math.radians(lat)), 110574.0

    def area(geom):
        return transform(lambda x, y, z=None: (x * mx, y * my), geom).area

    keys = sorted(districts, key=lambda k: (len(k), k))
    overlap = 0.0
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            inter = districts[a].intersection(districts[b])
            if not inter.is_empty:
                overlap += area(inter)
    if overlap > max_overlap_m2:
        fail("districts overlap by %.1f m2 (ceiling %.1f)" % (overlap, max_overlap_m2))
    covered = area(unary_union(list(districts.values())).intersection(county_geom)) / area(county_geom)
    if covered < min_covered:
        fail("the districts cover only %.4f%% of the county" % (100 * covered))
    return overlap, covered


def round_geom(geom, mapping):
    def fix(coords):
        if isinstance(coords[0], (float, int)):
            return [round(coords[0], COORD_PRECISION), round(coords[1], COORD_PRECISION)]
        return [fix(c) for c in coords]
    geo = mapping(geom)
    return {"type": geo["type"], "coordinates": fix(geo["coordinates"])}


def rings_of(geometry):
    if geometry["type"] == "Polygon":
        return geometry["coordinates"]
    return [r for poly in geometry["coordinates"] for r in poly]


def verify_point_in_rings(composition, vtds, district_features, point_in_rings, fail):
    """Re-run the APP'S OWN even-odd test against the rounded output, so a
    rounding artefact cannot ship a precinct into the wrong district."""
    for dnum, names in composition.items():
        for name in names:
            probe = vtds[norm(name)]["geom"].representative_point()
            hits = [f["properties"]["district"] for f in district_features
                    if point_in_rings(probe.y, probe.x, rings_of(f["geometry"]))]
            if hits != [dnum]:
                fail("precinct %s lands in district %s after rounding, expected %s"
                     % (name, hits or "none", dnum))


def write_or_check(paths_bodies, check, repo_root, fail, label):
    if check:
        for path, body in paths_bodies:
            if not os.path.exists(path):
                fail("%s is missing — run this script" % os.path.relpath(path, repo_root))
            with open(path, encoding="utf-8") as handle:
                if handle.read() != body:
                    fail("%s differs from a fresh build" % os.path.relpath(path, repo_root))
        print("  --check OK — every file matches a fresh build")
        return
    for path, body in paths_bodies:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(body)
    print("  wrote %s" % ", ".join(
        "%s (%s bytes)" % (os.path.relpath(p, repo_root), "{:,}".format(len(b)))
        for p, b in paths_bodies))


def dumps(payload):
    return json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
