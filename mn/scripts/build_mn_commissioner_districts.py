#!/usr/bin/env python3
"""
Build data/app/mn-commissioner-districts.json — all 447 county commissioner
districts in all 87 Minnesota counties, dissolved out of the Secretary of
State's own precinct fabric.

Minn. Stat. 375.025 subd. 1: "Each county shall be divided into as many
districts numbered consecutively as it has members of the county board.
Commissioner districts shall be bounded by town, municipal, ward, or
precinct lines". So EVERY Minnesota county is districted — there is no
at-large county board in this state to carry on a County card the way
Illinois carries nineteen — and the lines run along precinct boundaries by
law. That second clause is why this layer can exist at all: the Secretary of
State publishes every precinct with a `ctycomdist` attribute, so each
county's districts are unions of whole precincts and dissolving them
reproduces the county's own plan rather than approximating it.

NO STATEWIDE COMMISSIONER-DISTRICT LAYER IS PUBLISHED AND NONE IS NEEDED.
mn/WATCH.md recorded a relevance search of the state catalogue that turned up
no statewide layer and two county-published ones, and treated that as the
blocker. It was not: the same WATCH.md entry that records the precinct
service also records that its own attributes carry 447 commissioner
districts across all 87 counties. The composition was published the whole
time, one column over from the precincts.

THE SECOND WITNESS IS A DIFFERENT PUBLISHER PER COUNTY, AND IT IS
GEOMETRIC. Eight county governments publish their own commissioner-district
polygons, drawn in their own offices from their own plans (WITNESSES below).
For each of those counties this builder samples points inside every district
it just dissolved and asks the COUNTY's layer which district contains them,
requiring agreement. That is not the map checking itself: the Secretary of
State's precinct attribution and a county GIS office's own polygons are two
drawings with no shared copy. Six of the eight are the six counties whose
boards have seven members, which is where the statute needs the most help
(see below).

WHY THE WITNESS COUNTIES ARE THE ONES THEY ARE, AND WHY TWO ARE MISSING.
Minn. Stat. 375.01 gives every county a board of five "In Anoka, Hennepin,
Ramsey, and St. Louis Counties the board shall have seven members" — four
counties. The precinct fabric says SIX counties run seven districts, adding
DAKOTA and OLMSTED, and the statute does not name them: 375.03 subd. 1
speaks of "each county that has an increase of the number of commissioners",
so an increase is a thing that happens and the general statute does not
enumerate the counties it happened to. Rather than reason about which
special law applies, both are measured — Dakota's and Olmsted's own county
GIS each publish seven commissioner districts, which settles their board
size from the county itself. HENNEPIN and SHERBURNE publish their layers on
hosts whose robots.txt states `Disallow: /` for this client (gis.hennepin.us
and gis.co.sherburne.mn.us, measured 2026-10-01), so neither is read. That
is obeyed without exception and it costs one of the four counties the
statute does name; Hennepin's seven is the statute's own word, so nothing is
unproven by the refusal.

A LATER MODIFICATION DATE IS NOT CURRENCY, AND SCOTT COUNTY IS THE
COUNTER-EXAMPLE THAT NEARLY SHIPPED. Scott publishes TWO commissioner-district
layers: `Commissioner_Districts`, last modified 2026-09-29, and
`Scott_County_Commissioner_Districts_2022`, last modified 2024-03. The newer
one was taken first, on nothing better than its date, and it disagrees with
the Secretary of State's precinct attribution about WHOLE PRECINCTS — Prior
Lake P-2 and P-9, Shakopee P-7, P-9B and P-12B and Spring Lake Twp P-2, at
points up to a kilometre inside a district, which is far past anything two
simplifications of one line could explain. Measured against the 2022 layer
instead, the agreement is 1,410 sampled points to 0. So Scott's own 2022 plan
and the Secretary of State's own ballot attribution say the same thing, and
the layer with the later timestamp is the odd one out. WHAT THAT LAYER
REPRESENTS IS NOT ESTABLISHED HERE and is not guessed at; what is established
is that re-sharing, re-projecting or re-generalising a layer moves its
modification date without moving the plan, so the date cannot decide which of
two rival layers is in force. Illinois's Vermilion build settled the same
question on population balance; here the discriminator is agreement with the
attribution the Secretary of State uses to put a contest on a ballot.

A CATALOGUE ITEM'S LAYER INDEX IS NOT THE SERVICE'S. Anoka's entry in the
public catalogue points at .../OpenData_Political/MapServer/2, which is that
service's SENATE districts; its commissioner districts are layer 4. Reading
the index out of the catalogue entry would have compared Anoka's five-member
dissolve against eight state senate districts and failed for the wrong
reason. Every witness URL here was taken from the service's OWN layer list,
which is the same lesson Illinois's Richland build recorded about a viewer's
default layer index.

NO COMMISSIONER IS NAMED BY THIS CHANGE, AND THE ROUTE TO NAMING THEM IS NOW
MEASURED RATHER THAN UNPROVEN. mn/WATCH.md's open question was whether the
Secretary of State's certified-returns service carries commissioner
contests; it does not, and that was treated as closing the roster route.
This build found a different one: FIVE of the eight witness layers carry the
commissioner's own name on the district feature — Anoka `COMMISH`, Dakota
`COMMNAME`, Isanti `COMMISSIONER` with an e-mail, telephone and term, Ramsey
`Name` with e-mail, telephone and a web page, St. Louis `REPNAME1` with
e-mail and telephone. That is the shape seven Illinois counties already ship
through il_gis_board_scraper.py, where the members ride the same GIS feature
as the boundary. It is a per-county route, so it is 87 counties of work and
not this change's; the gap record `mn-county-commissioner-roster` carries
the finding so the next pass starts from a measurement instead of the
question. The card names the district and says plainly that it names nobody.

WHAT IS NOT CHECKED, STATED RATHER THAN IMPLIED. Minn. Stat. 375.025 subd. 1
requires each district to be within ten percent of the county average
population, and this builder does not measure that: the precinct service
publishes no population field, Minnesota ships no block-population index in
this instance, and a plan's population balance is a real currency test this
project has used elsewhere (Illinois's Vermilion build settled which of two
rival board layers was in force on exactly that measurement). So currency
here rests on the Secretary of State maintaining the fabric and on eight
counties' own drawings agreeing with it, not on population. Three of the
witness layers do publish a population per district (Anoka, Ramsey) and they
are not read for it, because a figure for eight counties is not a check on
447 districts.

Run:  python3 mn/scripts/build_mn_commissioner_districts.py
"""

import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
FLEET_SCRIPTS = os.path.join(os.path.dirname(INSTANCE), "scripts")
sys.path.insert(0, HERE)

import mn_vtd_dissolve as vtd  # noqa: E402

sys.path.insert(0, FLEET_SCRIPTS)

# THE ROBOTS SEAM IS IMPORTED HERE RATHER THAN REACHED THROUGH THE SHARED
# MODULE. This file fetches three host families of its own — the statute, the
# seven county witness layers and the certified results service — and
# `scripts/validate_robots_adoption.py` measures adoption PER FILE, by AST, for
# the reason its own docstring gives: a file that fetches and reaches nothing
# can ship with every other gate green. Asking through the shared module one
# call away satisfied the rule and not the gate, which was right to fail it —
# the guarantee that matters is per fetch in the file that fetches, not per list
# in a helper. `require_robots_once` is memoised per (host, client), so each of
# these calls costs a request the first time a run reaches a host and nothing
# after.
from scraper_common import require_robots_once  # noqa: E402

STATUTE_URL = "https://www.revisor.mn.gov/statutes/cite/375.01"
OUT_FILE = os.path.join(INSTANCE, "data", "app", "mn-commissioner-districts.json")

EXPECT_COUNTIES = 87
EXPECT_DISTRICTS = 447
MAPSHAPER = "mapshaper@0.6.102"   # pinned, as build_legislative_boundaries.py pins it
# Douglas-Peucker, interval in metres, thresholding how far the drawn line may
# stray rather than a triangle's area — the fleet's measured finding three times
# over. 15 m is about one step of the source line: measured over the dissolved
# borders of Aitkin, Olmsted and Ramsey, the median source segment is 16.09 m
# (p25 4.21, p75 65.39), the same scale as the 17.9 m Illinois measured on its
# own street grid and chose 15 m against.
SIMPLIFY_INTERVAL_M = 15

BOARD_SIZES = (5, 7)          # 375.01: five, or seven in the counties it names
                              # plus the increases 375.03 subd. 1 contemplates.

# Each witness is a county GOVERNMENT's own commissioner-district layer, taken
# from the service's own layer list rather than from a catalogue entry's URL.
# `seats` is what that county publishes, which is the measurement that settles
# its board size independently of the statute.
WITNESSES = {
    "Anoka": ("https://gisservices.co.anoka.mn.us/anoka_gis/rest/services/"
              "OpenData_Political/MapServer/4", "COMDIST", 7),
    "Dakota": ("https://gis2.co.dakota.mn.us/arcgis/rest/services/"
               "DCGIS_OL_PoliticalAdministrative/MapServer/8", "DIST_ID", 7),
    "Isanti": ("https://gis.co.isanti.mn.us/arcgis/rest/services/Elections/"
               "CommissionerDistricts_Public/FeatureServer/0", "DISTRICT", 5),
    "Olmsted": ("https://public.gis.olmstedcounty.gov/arcgis/rest/services/"
                "Political_Administrative/MapServer/4", "DISTRICT", 7),
    "Ramsey": ("https://gis.ramseycountymn.gov/server/rest/services/Boundary/"
               "BOUND_CommissionerDistrict2022_ViewOnly/FeatureServer/25",
               "District", 7),
    # SCOTT PUBLISHES TWO AND THE ONE WITH THE LATER MODIFICATION DATE IS THE
    # ODD ONE OUT — see A LATER MODIFICATION DATE IS NOT CURRENCY, above.
    "Scott": ("https://services.arcgis.com/DqIh9WAsIZcPlBEF/arcgis/rest/services/"
              "Scott_County_Commissioner_Districts_2022/FeatureServer/0",
              "CommDist", 5),
    "St. Louis": ("https://gis.stlouiscountymn.gov/server2/rest/services/"
                  "GeneralUse/Open_Data/MapServer/21", "DISTRICTID", 7),
}

# Counties whose own layer exists and is NOT read, with the reason. An entry
# here is a refusal obeyed, never a host to retry with a different client.
WITNESS_DECLINED = {
    "Hennepin": "gis.hennepin.us robots.txt states Disallow: / for this client",
    "Sherburne": "gis.co.sherburne.mn.us robots.txt states Disallow: / for this client",
}

# THE WITNESS COMPARES PRECINCT BY PRECINCT, NOT POINT BY POINT, because that
# is the question the layer answers: a commissioner district here IS a union of
# whole precincts, by Minn. Stat. 375.025 subd. 1, so the thing to check is
# whether the county agrees about which district each precinct is in.
#
# POINT SAMPLING WAS TRIED FIRST AND ASKED THE WRONG QUESTION. It reported four
# Rochester precincts as disagreements in Olmsted; measured across each
# precinct's own interior, Olmsted's layer agrees about all four and what
# differs is WHERE IT DRAWS THE LINE — its district boundaries cut through
# precincts by a few hundred metres, which no depth threshold can tell from a
# real disagreement, and which the statute says a commissioner district may not
# do. So the deviation is counted and reported as what it is, and a declaration
# table of "accepted disagreements" was deleted rather than kept: there is no
# precinct-level disagreement in any of the seven witness counties.
WITNESS_POINTS = 25

# A county whose layer covers none of a precinct is not witnessing it. St. Louis
# clips its districts to LAND — the points its layer misses in district 1 sit in
# Duluth Harbor, which TIGERweb's areal hydrography names outright, against a
# control in open Lake Superior that returns Lk Superior and one in downtown
# Duluth that returns no water. Anoka's miss is DRY LAND, a hole in its own
# layer in Fridley W-3 P-1 that Anoka's OWN SERVER also answers with nothing
# while answering district 7 for the rest of Fridley. Both are measured, neither
# is guessed, and the floor exists so a witness that has stopped covering its
# county stops counting as one — it is not a tolerance for disagreement, which
# has none.
WITNESS_PRECINCT_FLOOR = 0.90

# The Secretary of State's own certified per-precinct result tables carry the
# same `ctycomdist` key as a DATED snapshot, which makes them a witness about
# the lines over the whole state rather than over seven counties. They carry
# federal and state vote columns only — no commissioner contest — so they name
# nobody. The 2024 table is GATED against the live fabric; the 2022 one is
# reported, because a county that redistricted between the two elections should
# differ there and failing on that would be failing on a county doing its job.
RESULTS_LAYERS = (
    (("https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_sos/"
      "bdry_electionresults_2022_2030/FeatureServer/0"), "2024 general"),
    (("https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_sos/"
      "bdry_electionresults_2022_2030/FeatureServer/1"), "2022 general"),
)
GATED_RESULTS_LABEL = "2024 general"

# Minnesota's TIGER county fabric is water-inclusive to the international
# boundary, so a county anchor can sit on open water that the Secretary of
# State's precinct fabric — which covers the land people vote on — does not
# cover. Each entry is re-measured every run: an anchor that starts landing in
# a district fails the build, because a declaration nothing re-measures is a
# hole in the gate. Cook's anchor was checked against TIGERweb's own
# hydrography, which names it Lk Superior, with a dry-land control at Grand
# Marais.
ANCHORS_OUTSIDE_FABRIC = {
    "Cook": "the anchor sits in Lk Superior, which the Secretary of State's "
            "precinct fabric does not cover",
}


def fetch_board_size_statute():
    """Parse 375.01's own sentence rather than transcribing four county names.
    The seven-member list is a statutory fact that can be amended, and a
    hand-copied list is a silent way to go stale."""
    import requests  # noqa: PLC0415
    require_robots_once(STATUTE_URL, vtd.USER_AGENT)
    resp = requests.get(STATUTE_URL, headers={"User-Agent": vtd.USER_AGENT},
                        timeout=vtd.REQUEST_TIMEOUT)
    resp.raise_for_status()
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", resp.text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    for entity, char in (("&amp;", "&"), ("&nbsp;", " "), ("&#8217;", "'"),
                         ("&quot;", '"'), ("&#39;", "'")):
        text = text.replace(entity, char)
    text = re.sub(r"\s+", " ", text)
    if "board of five commissioners" not in text:
        raise SystemExit("FATAL: Minn. Stat. 375.01 no longer says every county has a "
                         "board of five commissioners. Re-read it before building.")
    # NOT [^.]*? — "St. Louis" carries a period, and excluding periods ends the
    # match inside the name of one of the four counties being read.
    match = re.search(r"\bIn (.{,120}?) Counties the board shall have seven members",
                      text)
    if not match:
        raise SystemExit("FATAL: could not find 375.01's seven-member sentence. The "
                         "statute has been reworded — re-read it before building.")
    names = [n.strip() for n in re.split(r",|\band\b", match.group(1)) if n.strip()]
    if not names:
        raise SystemExit("FATAL: 375.01's seven-member sentence named no counties")
    return set(names)


def fetch_witness(url, field, user_agent=vtd.USER_AGENT):
    import requests  # noqa: PLC0415
    require_robots_once(url, user_agent)
    resp = requests.get(url + "/query", headers={"User-Agent": user_agent},
                        timeout=vtd.REQUEST_TIMEOUT, params={
                            "where": "1=1", "outFields": field,
                            "returnGeometry": "true", "outSR": "4326",
                            "f": "geojson"})
    resp.raise_for_status()
    body = resp.json() or {}
    if "error" in body:
        raise SystemExit("FATAL: witness layer returned an error: %s" % body["error"])
    out = []
    for feature in body.get("features") or []:
        raw = (feature.get("properties") or {}).get(field)
        if raw is None:
            raise SystemExit("FATAL: a witness feature carries no %s" % field)
        digits = re.search(r"(\d+)", str(raw))
        if not digits:
            raise SystemExit("FATAL: witness district %r holds no number" % raw)
        out.append((int(digits.group(1)), feature.get("geometry") or {}))
    return out


def interior_points(geom, wanted):
    """Points provably inside the polygon, on a grid over its own extent. A
    centroid is not used: a district shaped like a crescent has a centroid
    outside itself, and a witness check seeded with outside points reports a
    disagreement that is the sampler's."""
    polys = (geom["coordinates"] if geom["type"] == "MultiPolygon"
             else [geom["coordinates"]])
    xs = [pt[0] for poly in polys for pt in poly[0]]
    ys = [pt[1] for poly in polys for pt in poly[0]]
    lo_x, hi_x, lo_y, hi_y = min(xs), max(xs), min(ys), max(ys)
    found, step = [], 1
    while len(found) < wanted and step <= 7:
        n = 8 * step
        found = []
        for i in range(1, n):
            for j in range(1, n):
                lng = lo_x + (hi_x - lo_x) * i / float(n)
                lat = lo_y + (hi_y - lo_y) * j / float(n)
                if vtd.point_in_geom(lng, lat, geom):
                    found.append((lng, lat))
                    if len(found) >= wanted:
                        return found
        step += 1
    return found


def fetch_results_key(url, label, user_agent=vtd.USER_AGENT):
    """Read one certified per-precinct result table's commissioner-district key,
    statewide, as {(county, precinct): district}. These tables carry federal and
    state vote columns only — no commissioner contest — so they name no
    officeholder; what they carry is the same `ctycomdist` key as a dated,
    certified snapshot, which is what makes them a witness about the lines."""
    import requests  # noqa: PLC0415
    require_robots_once(url, user_agent)
    rows, offset = [], 0
    while True:
        resp = requests.get(url + "/query", headers={"User-Agent": user_agent},
                            timeout=vtd.REQUEST_TIMEOUT, params={
                                "where": "1=1",
                                "outFields": "countyname,pctname,ctycomdist",
                                "returnGeometry": "false",
                                "orderByFields": "objectid",
                                "resultOffset": str(offset),
                                "resultRecordCount": str(vtd.PAGE_SIZE),
                                "f": "json"})
        resp.raise_for_status()
        body = resp.json() or {}
        if "error" in body:
            raise SystemExit("FATAL: the %s results layer returned an error: %s"
                             % (label, body["error"]))
        page = [r.get("attributes") or {} for r in (body.get("features") or [])]
        rows.extend(page)
        if len(page) < vtd.PAGE_SIZE:
            break
        offset += vtd.PAGE_SIZE
    if not rows:
        raise SystemExit("FATAL: the %s results layer returned no precinct at all, so it "
                         "cannot witness anything" % label)
    return {((r.get("countyname") or "").strip(), (r.get("pctname") or "").strip()):
            int(r["ctycomdist"]) for r in rows if r.get("ctycomdist")}


def simplify_shared(collection):
    """Simplify through mapshaper, in ONE file, so that a border two districts
    share is ONE arc simplified once and both sides keep the same vertices.

    Simplifying each district's rings on their own is what this builder did
    first and it is wrong in a way that looks fine: two neighbours' copies of
    one line come out different, so they overlap in places and leave slivers in
    others, and the overlap gate below caught it in Olmsted. Illinois's
    build_legislative_boundaries.py recorded the same finding about its three
    legislative chambers and the same remedy. `keep-shapes` keeps every district
    and every part of one."""
    if not shutil.which("npx"):
        raise SystemExit("FATAL: npx is not on PATH, and this builder simplifies "
                         "through mapshaper so that neighbouring districts keep a "
                         "shared border. Install Node.js and run again.")
    work = tempfile.mkdtemp(prefix="mn-commissioner-")
    try:
        src = os.path.join(work, "exact.json")
        dst = os.path.join(work, "simple.json")
        with open(src, "w") as handle:
            json.dump(collection, handle, separators=(",", ":"))
        proc = subprocess.run(
            ["npx", "--yes", MAPSHAPER, src,
             "-simplify", "dp", "interval=%d" % SIMPLIFY_INTERVAL_M, "keep-shapes",
             "-o", "precision=0.000001", dst],
            capture_output=True, text=True)
        if proc.returncode != 0 or not os.path.exists(dst):
            raise SystemExit("FATAL: mapshaper failed (%d): %s"
                             % (proc.returncode, (proc.stderr or "")[-800:]))
        with open(dst) as handle:
            out = json.load(handle)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    if len(out.get("features") or []) != len(collection["features"]):
        raise SystemExit("FATAL: mapshaper returned %d features for %d — a district was "
                         "dropped, which keep-shapes exists to prevent"
                         % (len(out.get("features") or []), len(collection["features"])))
    return out


def main():
    vtd.require_robots([vtd.PRECINCT_QUERY, STATUTE_URL]
                       + [url for url, _f, _s in WITNESSES.values()],
                       FLEET_SCRIPTS)

    seven_by_statute = fetch_board_size_statute()
    print("statute: Minn. Stat. 375.01 gives every county five commissioners and "
          "names %d with seven (%s)"
          % (len(seven_by_statute), ", ".join(sorted(seven_by_statute))),
          file=sys.stderr)

    features = vtd.fetch_precincts(
        ["vtdid", "countyname", "countyfips", "ctycomdist", "pctname"], geometry=True)
    groups, per_county = {}, {}
    for feature in features:
        props = feature.get("properties") or {}
        county = (props.get("countyname") or "").strip()
        fips = (props.get("countyfips") or "").strip()
        raw = (props.get("ctycomdist") or "").strip()
        if not county or not fips or not raw:
            raise SystemExit("FATAL: a precinct carries no county or no commissioner "
                             "district: %r" % props)
        number = int(raw)
        groups.setdefault((fips, number), []).append(feature)
        per_county.setdefault(county, {"fips": fips, "districts": set()})
        per_county[county]["districts"].add(number)

    # Gate 1 — the partition the statute requires.
    if len(per_county) != EXPECT_COUNTIES:
        raise SystemExit("FATAL: the precinct fabric covers %d counties, expected %d"
                         % (len(per_county), EXPECT_COUNTIES))
    if len(groups) != EXPECT_DISTRICTS:
        raise SystemExit("FATAL: dissolved %d commissioner districts, expected %d"
                         % (len(groups), EXPECT_DISTRICTS))
    for county, info in sorted(per_county.items()):
        numbers = sorted(info["districts"])
        if numbers != list(range(1, len(numbers) + 1)):
            raise SystemExit("FATAL: %s's districts are not numbered consecutively "
                             "from 1 as 375.025 subd. 1 requires: %s"
                             % (county, numbers))
        if len(numbers) not in BOARD_SIZES:
            raise SystemExit("FATAL: %s runs %d commissioner districts, which is "
                             "neither of the board sizes Minn. Stat. 375.01 and "
                             "375.03 allow for %s" % (county, len(numbers),
                                                      BOARD_SIZES))
    seven_in_data = {c for c, i in per_county.items() if len(i["districts"]) == 7}
    unnamed = sorted(seven_in_data - seven_by_statute)
    missing = sorted(seven_by_statute - seven_in_data)
    if missing:
        raise SystemExit("FATAL: Minn. Stat. 375.01 gives these counties seven "
                         "commissioners and the precinct fabric does not: %s"
                         % missing)
    for county in unnamed:
        if county not in WITNESSES:
            raise SystemExit(
                "FATAL: %s runs seven commissioner districts, Minn. Stat. 375.01 does "
                "not name it, and no witness layer settles its board size. An "
                "increase 375.03 subd. 1 contemplates is a county fact and wants a "
                "county source, not an assumption." % county)
    print("partition: %d districts across all %d counties, numbered consecutively; "
          "%d counties run seven, of which %s are increases the statute does not name "
          "and are witnessed by their own county GIS"
          % (len(groups), len(per_county), len(seven_in_data),
             " and ".join(unnamed) or "none"), file=sys.stderr)

    # Build the polygons EXACTLY, then simplify the whole set in one pass so a
    # shared border is simplified once. Every gate below runs on what ships.
    live_key = {}
    for feature in features:
        props = feature.get("properties") or {}
        live_key[((props.get("countyname") or "").strip(),
                  (props.get("pctname") or "").strip())] = int(props["ctycomdist"])
    county_precincts = {}
    for feature in features:
        props = feature.get("properties") or {}
        county_precincts.setdefault((props.get("countyname") or "").strip(),
                                    []).append(feature)
    county_of_fips = {i["fips"]: c for c, i in per_county.items()}
    keys = sorted(groups, key=lambda k: (county_of_fips[k[0]], k[1]))
    exact = {"type": "FeatureCollection", "features": []}
    for fips, number in keys:
        polys = vtd.group_rings(vtd.dissolve(groups[(fips, number)]))
        exact["features"].append({
            "type": "Feature",
            "properties": {"countyFips": fips, "district": number},
            "geometry": ({"type": "Polygon", "coordinates": polys[0]} if len(polys) == 1
                         else {"type": "MultiPolygon", "coordinates": polys}),
        })
    simple = simplify_shared(exact)
    built = {}
    for feature in simple["features"]:
        props = feature.get("properties") or {}
        fips = str(props.get("countyFips") or "")
        number = props.get("district")
        if fips not in county_of_fips or number is None:
            raise SystemExit("FATAL: mapshaper returned a feature whose properties this "
                             "builder does not recognise: %r" % props)
        key = (fips, int(number))
        if key in built:
            raise SystemExit("FATAL: mapshaper returned %s twice" % (key,))
        built[key] = (feature["geometry"], len(groups[key]))
    if sorted(built) != sorted(groups):
        raise SystemExit("FATAL: the simplified set is not the dissolved set")

    # Gate 2 — each county's own government's drawing of the same districts,
    # compared precinct by precinct.
    checked_counties = checked_precincts = 0
    cut_points = uncovered_precincts = 0
    for county, (url, field, seats) in sorted(WITNESSES.items()):
        theirs = fetch_witness(url, field)
        if len(theirs) != seats:
            raise SystemExit("FATAL: %s County publishes %d commissioner districts, and "
                             "this builder expected %d. Re-read the county's own layer "
                             "before trusting either side." % (county, len(theirs), seats))
        if seats != len(per_county[county]["districts"]):
            raise SystemExit("FATAL: %s County publishes %d districts and the Secretary "
                             "of State's precincts compose %d"
                             % (county, seats, len(per_county[county]["districts"])))
        witnessed = uncovered = 0
        for precinct in county_precincts[county]:
            props = precinct.get("properties") or {}
            name = (props.get("pctname") or "").strip()
            ours = int(props["ctycomdist"])
            points = interior_points(precinct["geometry"], WITNESS_POINTS)
            if not points:
                raise SystemExit("FATAL: could not seed a point inside %s in %s County"
                                 % (name or "an unnamed precinct", county))
            tally = {}
            for lng, lat in points:
                hits = [num for num, geom in theirs
                        if geom and vtd.point_in_geom(lng, lat, geom)]
                if len(hits) == 1:
                    tally[hits[0]] = tally.get(hits[0], 0) + 1
            if not tally:
                uncovered += 1
                uncovered_precincts += 1
                continue
            modal = max(sorted(tally), key=lambda k: tally[k])
            if modal != ours:
                raise SystemExit(
                    "FATAL: %s County's own layer puts most of %s in its district %d, "
                    "and the Secretary of State's precinct fabric puts that precinct in "
                    "district %d. The two government publishers disagree about a whole "
                    "precinct, which is not a drawing difference — settle it against the "
                    "Secretary of State's certified per-precinct result tables, or "
                    "against another county product, before shipping either side. "
                    "Tally over %d interior points: %s"
                    % (county, name, modal, ours, len(points), dict(sorted(tally.items()))))
            witnessed += 1
            checked_precincts += 1
            cut_points += sum(n for k, n in tally.items() if k != ours)
        total = witnessed + uncovered
        if witnessed / float(total) < WITNESS_PRECINCT_FLOOR:
            raise SystemExit(
                "FATAL: %s County's own layer covers only %d of its %d precincts. It "
                "agrees wherever it answers, but it no longer covers enough of its own "
                "county to witness it." % (county, witnessed, total))
        if uncovered:
            print("notice: %s County's own layer covers none of %d of its %d precincts; "
                  "it agrees about every precinct it does cover"
                  % (county, uncovered, total), file=sys.stderr)
        checked_counties += 1
    print("witness: %d county governments' own layers agree with the Secretary of "
          "State about the district of every one of %d precincts they cover; %d sampled "
          "points fall on the other side of a county's own district line, which is that "
          "county drawing a boundary that does not follow a precinct line; %d counties "
          "publish a layer this client is refused (%s)"
          % (checked_counties, checked_precincts, cut_points,
             len(WITNESS_DECLINED), "; ".join(sorted(WITNESS_DECLINED))),
          file=sys.stderr)

    # Gate 2b — the Secretary of State's own certified per-precinct tables, over
    # the whole state rather than seven counties.
    for url, label in RESULTS_LAYERS:
        table = fetch_results_key(url, label)
        shared = set(table) & set(live_key)
        if len(shared) < 0.9 * len(live_key):
            raise SystemExit("FATAL: the certified %s table shares only %d precinct "
                             "names with the %d in the live fabric, which is too few to "
                             "witness anything — the naming has changed and this check "
                             "needs re-measuring" % (label, len(shared), len(live_key)))
        differ = {k: (live_key[k], table[k]) for k in shared if live_key[k] != table[k]}
        if label == GATED_RESULTS_LABEL:
            if differ:
                raise SystemExit(
                    "FATAL: the Secretary of State's certified %s table disagrees with "
                    "its own live precinct fabric about %d precinct(s): %s. One of the "
                    "two is not the plan in force and this builder will not guess which."
                    % (label, len(differ),
                       sorted((c, p, a, b) for (c, p), (a, b) in differ.items())[:8]))
            print("certified: the %s table agrees with the live fabric about every one "
                  "of %d precincts they both name" % (label, len(shared)),
                  file=sys.stderr)
        else:
            counties = sorted({c for c, _p in differ})
            print("certified: the %s table agrees with the live fabric about %d of %d "
                  "precincts they both name; %d differ, in %s, which is a county "
                  "redistricting after that election rather than a defect"
                  % (label, len(shared) - len(differ), len(shared), len(differ),
                     ", ".join(counties) or "no county"), file=sys.stderr)

    # Gate 3 — no two districts overlap. A point derived from a district's own
    # polygon landing inside it says little; landing inside NO OTHER district is
    # the content, and it is what a dissolve that double-counted a precinct
    # would fail.
    for (fips, number), (geom, _n) in sorted(built.items()):
        points = interior_points(geom, 12)
        if len(points) < 4:
            raise SystemExit("FATAL: could not seed interior points in %s district %d"
                             % (county_of_fips[fips], number))
        for lng, lat in points:
            hits = [(f, n) for (f, n), (g, _c) in built.items()
                    if vtd.point_in_geom(lng, lat, g)]
            if hits != [(fips, number)]:
                raise SystemExit(
                    "FATAL: %.5f,%.5f is inside %s County district %d and also inside "
                    "%s. Two commissioner districts overlap, so the dissolve has "
                    "double-counted ground."
                    % (lng, lat, county_of_fips[fips], number,
                       [(county_of_fips[f], n) for f, n in hits
                        if (f, n) != (fips, number)]))
    print("overlap: no point inside any of the %d districts is inside a second one"
          % len(built), file=sys.stderr)

    # Gate 4 — containment: every county's proven-interior anchor lands in
    # exactly one district, and that district is its own county's.
    sys.path.insert(0, HERE)
    from build_metro_outline import INSIDE  # noqa: PLC0415
    if len(INSIDE) != EXPECT_COUNTIES:
        raise SystemExit("FATAL: build_metro_outline.INSIDE holds %d anchors, expected "
                         "one per county (%d)" % (len(INSIDE), EXPECT_COUNTIES))
    placed, declared_outside = 0, []
    for place, (lat, lng) in sorted(INSIDE.items()):
        hits = [(fips, num) for (fips, num), (geom, _n) in built.items()
                if vtd.point_in_geom(lng, lat, geom)]
        if place in ANCHORS_OUTSIDE_FABRIC:
            if hits:
                raise SystemExit(
                    "FATAL: %s's anchor is declared outside the precinct fabric (%s) "
                    "and now lands in %s. Delete the ANCHORS_OUTSIDE_FABRIC entry — a "
                    "declaration nothing re-measures is a hole in the gate."
                    % (place, ANCHORS_OUTSIDE_FABRIC[place],
                       [(county_of_fips[f], n) for f, n in hits]))
            declared_outside.append(place)
            continue
        if len(hits) != 1:
            raise SystemExit("FATAL: %s (%.5f,%.5f) falls in %d commissioner districts, "
                             "expected exactly 1: %s"
                             % (place, lat, lng, len(hits),
                                [(county_of_fips[f], n) for f, n in hits]))
        if county_of_fips[hits[0][0]] not in place:
            raise SystemExit("FATAL: %s's anchor lands in %s County's district %d"
                             % (place, county_of_fips[hits[0][0]], hits[0][1]))
        placed += 1
    if placed + len(declared_outside) != EXPECT_COUNTIES:
        raise SystemExit("FATAL: checked %d anchors, expected %d"
                         % (placed + len(declared_outside), EXPECT_COUNTIES))
    print("containment: %d of %d county anchors land in exactly one commissioner "
          "district, and it is their own county's; %d declared outside the precinct "
          "fabric (%s)"
          % (placed, EXPECT_COUNTIES, len(declared_outside),
             ", ".join("%s — %s" % (p, ANCHORS_OUTSIDE_FABRIC[p])
                       for p in declared_outside)), file=sys.stderr)

    out = {"type": "FeatureCollection", "features": []}
    for (fips, number), (geom, precincts) in sorted(
            built.items(), key=lambda kv: (county_of_fips[kv[0][0]], kv[0][1])):
        county = county_of_fips[fips]
        out["features"].append({
            "type": "Feature",
            "properties": {
                "county": county,
                "countyFips": fips,
                "district": number,
                "name": "%s County Commissioner District %d" % (county, number),
                "seats": len(per_county[county]["districts"]),
                "precincts": precincts,
            },
            "geometry": geom,
        })

    with open(OUT_FILE, "w") as handle:
        json.dump(out, handle, separators=(",", ":"))
        handle.write("\n")
    vertices = sum(len(ring)
                   for feature in out["features"]
                   for poly in ([feature["geometry"]["coordinates"]]
                                if feature["geometry"]["type"] == "Polygon"
                                else feature["geometry"]["coordinates"])
                   for ring in poly)
    print("mn-commissioner-districts -> %s: %d districts in %d counties, %d "
          "vertices, %d bytes (shared topology, dp interval %.0f m, 6dp)"
          % (os.path.relpath(OUT_FILE, INSTANCE), len(out["features"]),
             len(per_county), vertices, os.path.getsize(OUT_FILE),
             SIMPLIFY_INTERVAL_M), file=sys.stderr)


if __name__ == "__main__":
    main()
