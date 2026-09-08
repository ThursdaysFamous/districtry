#!/usr/bin/env python3
"""Build Logan County's seven park districts from the Tri-County Regional
Planning Commission's public ArcGIS service.

WHERE THIS CAME FROM
--------------------
Logan County publishes no park district boundary itself. TCRPC does, and the
service was found by an unauthenticated arcgis.com catalog search with nothing
read from the county at all. Its Logan_County_Districts_and_Zoning service has
53 layers; seven of them, ids 26-32, are single-feature polygons carrying only
FID/District/Shape__Area and named Atlanta, Armington, Chestnut Beason, Emden,
Lincoln, Mt. Pulaski and San Jose.

THE SERVICE DOES NOT SAY WHAT THEY ARE. Every parentLayerId is -1 because the
group headers were flattened out on publish (ids 2, 7, 8, 11, 17, 25, 33, 38,
41 and 48 are the gaps where their names used to be), there is no MapServer
sibling, and the item carries an empty description, one empty tag, empty
licenseInfo and empty accessInformation.

The first reading of these layers here was WRONG and is worth stating, because
it is the failure this builder is designed against. All seven names are also
Logan fire-agency names, and Illinois fire protection districts are named for
their towns, so they were read as fire districts. Three checks ruled out other
readings (they are not the K-12 school districts, not the dispatch fire zones
dissolved, not the library districts in the same service) but no check could
supply the subject, and a name pattern is not a subject.

What supplies it is TCRPC's own Logan County Public Web Map. The group headers
the FeatureServer lost survive in that web map's item data, and the heading over
exactly these seven ids reads "Park Districts". The same map names 49-56 Zoning,
9 Cemetery Districts and 18-23 Library Districts.

So THE WEB MAP GROUPING IS A GATE HERE, not a footnote. If TCRPC republishes and
those ids stop sitting under a park heading, this build fails rather than
shipping polygons whose subject is once again unknown.

LICENCE, AND WHERE TO RE-READ IT
--------------------------------
Measured, not assumed, because two Illinois counties are blocked on exactly this
question. It is also CITED to the right item, which the first version of this
file got wrong: it pointed a later auditor at the Feature Service item
(ef8ec7bd, SOURCE_URL below), whose licenseInfo AND accessInformation are both
EMPTY -- so the item named carried no terms at all -- while quoting an
attribution line ("TCRPC; IDOT; USDOT; US Census Bureau; USGS") that belongs to
a THIRD item, TCRPC Open Data (d245c708). Neither is the operative one.

THE OPERATIVE ITEM IS TCRPC's "Logan County Public Map Viewer", 9c2f6ed1
(TERMS_URL below). Its accessInformation reads "Logan County; Tri-County
Regional Planning Commission" and its licenseInfo is 1,879 characters of
no-warranty and no-liability disclaimer stating that the Information "is
provided as a public service". It carries no redistribution clause, no fee and
no signing requirement, which is the opposite of the clause that stopped
Whiteside and Winnebago. Three TCRPC GIS pages were also enumerated by LINK
rather than by prose -- the rule Whiteside taught -- and carry no licence
agreement, fee schedule or data request form.

The permissive reading was right and is unchanged. Pointing at the wrong item
was not a harmless slip: of 100 items published by these two TCRPC accounts, 78
carry an empty licenseInfo, three read "License Agreement" and one reads
"Internal Use Only", so an auditor sent to the wrong item can land on a
restrictive one.

A SECOND WITNESS IS AVAILABLE AND IS NOT YET READ, which is an open route rather
than a closed one. Certified county election results would be the independent
confirmation this grouping wants, and Logan County publishes them.

AN EARLIER VERSION OF THIS PARAGRAPH SAID THE SITE WAS CLOSED TO US, AND THAT
WAS A MISREADING OF ITS robots.txt. www.logancountyil.gov does list
`anthropic-ai` and `Claude-Web` with `Disallow: /`, but those are ANTHROPIC's
own crawler tokens and nothing in this repository sends either. This file sends
`districtry/1.0 (+https://districtry.com/)` (HEADERS, below), so the group that
binds it is the site's `User-agent: *` -- narrow Joomla paths only
(/administrator/, /cache/, /templates/ and the like), with the content allowed.
The repository has no single client string: other scripts send tokens such as
`districtry-link-check/1.0` and `DistrictExplorer-roster-bot/1.0`, and until
this change THIS builder sent the requests default. None of them is an
Anthropic crawler token, so the reading holds for all of them; the token is
pinned here so a later reader can check the claim against the robots group
instead of taking it on trust. A robots group
binds the agent whose token it names, and reading someone else's product token
as though it covered this scraper withholds data the site is in fact serving.
The operator settled this on 2026-09-08: the Anthropic tokens govern live
lookups and training collection, not the retrieval script districtry runs. Where
a `*` group DOES disallow -- Rochester Hills and Durand both do -- it binds this
project exactly as before, and those stay shut.

Until that route is read, the web map grouping stands alone, which is exactly
why the builder gates on it every run.

WHAT SHIPS
----------
The district name exactly as the service's own District column spells it. The
card labels the row "Park District", so "Atlanta" renders as "Park District:
Atlanta"; the formal name is presumably "Atlanta Park District" but the source
does not say so and this does not add words to it. Note the service spells one
district "Chestnut Beason" where the web map's layer title reads
"Chestnut - Beason"; the data's own field wins.

No trustee, address or telephone number is published for any of the seven. That
absence is recorded as its own gap rather than papered over.

Usage (rare operator step; network access to the TCRPC service required):
    pip install -c scripts/requirements.txt shapely requests
    python3 scripts/build_logan_park_districts.py
    python3 scripts/build_logan_park_districts.py --check   # drift gate
"""

import argparse
import json
import os
import re
import sys

import requests
from shapely import make_valid
from shapely.geometry import mapping, shape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "il", "data", "app", "logan-park-districts.json")
COUNTY_OUTLINE = os.path.join(ROOT, "il", "data", "app", "logan-county-outline.json")

SERVICE = ("https://services.arcgis.com/pPTAs43AFhhk0pXQ/arcgis/rest/services/"
           "Logan_County_Districts_and_Zoning/FeatureServer")
WEB_MAP_ITEM = "0f24e714999949c9a55dffd6a32eac3d"      # "Logan County Public Web Map"
SERVICE_NAME = "Logan_County_Districts_and_Zoning"
ITEM_DATA = "https://www.arcgis.com/sharing/rest/content/items/%s/data?f=json"

# layer id -> the District value the service publishes for it. Both halves are
# pinned: a changed id set or a changed name fails the build.
EXPECTED = {
    26: "Atlanta",
    27: "Armington",
    28: "Chestnut Beason",
    29: "Emden",
    30: "Lincoln",
    31: "Mt. Pulaski",
    32: "San Jose",
}
# The web map heading that has to sit above those ids. Matched case-insensitively
# on the words, so "Park Districts" and "Park District" both pass and anything
# else -- including no heading at all -- fails.
GROUP_WORD = "park"

# Identify the client. The robots reasoning in the LICENCE section is about
# WHICH group binds this fetcher, so the token has to be one this file really
# sends rather than one a docstring asserts.
HEADERS = {"User-Agent": "districtry/1.0 (+https://districtry.com/)"}

COORD_PRECISION = 6      # ~0.1 m
MIN_INSIDE_FRACTION = 0.60   # San Jose, the least contained, measured 0.647
MAX_OVERLAP_SHARE = 1e-4     # 0.01%; measured worst is 0.0002% (see below)

SOURCE_LABEL = "Tri-County Regional Planning Commission"
# The data. This item carries NO terms — licenseInfo and accessInformation are
# both empty — so it is the source and never the licence citation.
SOURCE_URL = ("https://www.arcgis.com/home/item.html?id="
              "ef8ec7bd1d4e465f94b1e9a08a899f25")
# The terms. TCRPC's "Logan County Public Map Viewer"; see the LICENCE section.
TERMS_URL = ("https://www.arcgis.com/home/item.html?id="
             "9c2f6ed1fcd94a61a4cb565c758a785e")


def fail(msg):
    sys.exit("build-logan-park-districts: FAIL — " + msg)


def get_json(url, what):
    try:
        r = requests.get(url, timeout=60, headers=HEADERS)
        r.raise_for_status()
        return r.json()
    except Exception as exc:                      # noqa: BLE001 - report and stop
        fail("could not fetch %s (%s): %s" % (what, url, exc))


def read_group_headings():
    """Return {layer id on OUR service: the group heading directly above it}.

    Keyed on the layer's URL, never on the web map's `id` field. Two reasons,
    the second learned by this build failing on its own first run: the `id`
    field is an internal string like "19d4ec7abdc-layer-24", and the numeric
    sublayer ids that DO appear in the map are not unique across it -- the
    Property > Additional Information MapServer also has layers 26, 27 and 32,
    so an id-keyed lookup reads a heading belonging to a different service and
    is wrong without looking wrong.
    """
    data = get_json(ITEM_DATA % WEB_MAP_ITEM, "the Logan County Public Web Map")
    headings = {}

    def walk(node, heading):
        if isinstance(node, list):
            for child in node:
                walk(child, heading)
            return
        if not isinstance(node, dict):
            return
        title = node.get("title")
        children = node.get("layers")
        if children:
            walk(children, title or heading)
            return
        url = node.get("url") or ""
        if SERVICE_NAME in url:
            m = re.search(r"/(\d+)$", url.rstrip("/"))
            if m and heading:
                headings[int(m.group(1))] = heading

    walk(data.get("operationalLayers") or [], None)
    if not headings:
        fail("read no %s layer groupings from the web map — its structure has "
             "moved, and without a heading these polygons have no published "
             "subject" % SERVICE_NAME)
    return headings


def load_county():
    with open(COUNTY_OUTLINE, encoding="utf-8") as fh:
        raw = json.load(fh)
    geom = raw["features"][0]["geometry"] if raw.get("type") == "FeatureCollection" else raw
    return make_valid(shape(geom))


def round_geom(geom):
    def walk(c):
        if isinstance(c[0], (int, float)):
            return [round(c[0], COORD_PRECISION), round(c[1], COORD_PRECISION)]
        return [walk(x) for x in c]
    m = mapping(geom)
    return {"type": m["type"], "coordinates": walk(m["coordinates"])}


def build():
    headings = read_group_headings()
    county = load_county()
    features = []

    for lid, expected_name in sorted(EXPECTED.items()):
        heading = headings.get(lid)
        if not heading or GROUP_WORD not in heading.lower():
            fail("layer %d sits under %r in the web map, not a park heading. That "
                 "grouping is the only thing that says these polygons are park "
                 "districts, so nothing is written." % (lid, heading))

        url = ("%s/%d/query?where=1%%3D1&outFields=District&outSR=4326&f=geojson"
               % (SERVICE, lid))
        payload = get_json(url, "layer %d" % lid)
        rows = payload.get("features") or []
        if len(rows) != 1:
            fail("layer %d returned %d features, expected exactly 1" % (lid, len(rows)))

        name = (rows[0].get("properties") or {}).get("District")
        name = (name or "").strip()
        if name != expected_name:
            fail("layer %d is named %r, expected %r — the service has been "
                 "republished and the pinned names need re-verifying"
                 % (lid, name, expected_name))

        geom = make_valid(shape(rows[0]["geometry"]))
        if geom.is_empty or geom.area <= 0:
            fail("%s has empty geometry" % name)

        inside = geom.intersection(county).area / geom.area
        if inside < MIN_INSIDE_FRACTION:
            fail("%s is only %.1f%% inside Logan County (floor %.0f%%) — either the "
                 "wrong county's data or a changed boundary"
                 % (name, 100 * inside, 100 * MIN_INSIDE_FRACTION))

        features.append({
            "type": "Feature",
            "properties": {"district": name},
            "geometry": round_geom(geom),
        })

    if len(features) != len(EXPECTED):
        fail("built %d districts, expected %d" % (len(features), len(EXPECTED)))

    # Park districts are separate taxing bodies and do not overlap. The test is
    # a FRACTION of the smaller district, not an absolute area, because five
    # adjacent pairs share a boundary and every one of them carries a
    # digitisation sliver: measured 2026-09-08, the largest is Atlanta against
    # Armington at 35.5 m², which is 0.0002% of the smaller of the two, and the
    # other four are 13.1 m² or less. A real double-claim is percent-scale (the
    # Cook fire tiling double-claims 57 acres), so the ceiling below fails on
    # anything fifty times worse than today's noise and cannot trip on vertex
    # wobble when TCRPC re-digitises.
    for i in range(len(features)):
        for j in range(i + 1, len(features)):
            a, b = shape(features[i]["geometry"]), shape(features[j]["geometry"])
            overlap = a.intersection(b).area
            share = overlap / min(a.area, b.area)
            if share > MAX_OVERLAP_SHARE:
                fail("%s and %s overlap over %.4f%% of the smaller district "
                     "(ceiling %.4f%%) — that is a double-claim, not a sliver"
                     % (features[i]["properties"]["district"],
                        features[j]["properties"]["district"],
                        100 * share, 100 * MAX_OVERLAP_SHARE))

    return {"type": "FeatureCollection", "features": features}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="rebuild and compare against the shipped file; write nothing")
    args = ap.parse_args()

    collection = build()
    rendered = json.dumps(collection, indent=1, sort_keys=True) + "\n"

    if args.check:
        if not os.path.exists(OUT):
            fail("%s is missing — run without --check" % OUT)
        with open(OUT, encoding="utf-8") as fh:
            if fh.read() != rendered:
                fail("%s does not match a fresh build of the TCRPC service" % OUT)
        print("build-logan-park-districts: OK — %d districts match the shipped file"
              % len(collection["features"]))
        return

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(rendered)
    print("build-logan-park-districts: wrote %s — %d districts (%s), source: %s"
          % (OUT, len(collection["features"]),
             ", ".join(f["properties"]["district"] for f in collection["features"]),
             SOURCE_LABEL))


if __name__ == "__main__":
    main()
