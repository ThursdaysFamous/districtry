#!/usr/bin/env python3
"""
Build in/data/app/in-conservancy-districts.json: Indiana's active
conservancy districts, from the Department of Natural Resources' map of
them.

    python3 in/scripts/build_in_conservancy_districts.py            # fetch, check, write
    python3 in/scripts/build_in_conservancy_districts.py --check    # offline
    python3 in/scripts/build_in_conservancy_districts.py --watch    # has the layer changed?

The work is scripts/published_district_layers.py, which other builders
share; this file says where the layer is, how to read one record and what to
expect. The boards' names are a separate file with a separate source, built
by in/scripts/build_in_conservancy_directors.py from the department's annual
directory, and that builder reads this file to know which districts are
drawn.

WHAT A CONSERVANCY DISTRICT IS. A unit of local government set up under the
Indiana Conservancy District Act (IC 14-33, passed in 1947) when property
owners petition a circuit court, for one or more water purposes: flood
control, drainage, sewage, water supply, a lake's upkeep and the like. Its
board of directors is elected by the property owners in the district (the
department's conservancy district page, read 2026-10-16). It is the
"special districts the state's own law creates" level of the fleet's done
standard (docs/DONE_STANDARD.md, entry 12), and the one family of Indiana
special districts a state office maps statewide with elected boards: the
State Library's library district map is the other statewide one, and those
boards are appointed.

THE SOURCE. "Conservancy Districts of Indiana", layer 54 of the Hosted
service of the same name on gisdata.in.gov, which the department keeps
(last edited 2026-07-14 when read). 130 records, measured 2026-10-16:

  * 103 carry status "Active" and are read (WHERE below); 15 "Dissolved"
    and 10 "Inactive" are not.
  * TWO RECORDS CARRY NO STATUS AT ALL, and neither is drawn: "Lake" (id 76)
    and "Hidden Hills" (id 140). The department's 2026 directory lists
    Hidden Hills, with nothing but its id and the sentence that it sent no
    list of officers; whether it is active is the department's to say, and
    the map leaves it blank.
  * THREE DISTRICTS ARE PUBLISHED IN TWO RECORDS EACH (ids 133, 137 and 138,
    every field equal), so 103 records draw 100 districts, joined into one
    shape each; the spec's multipart_records holds that count at three.
  * THREE DISTRICTS LIE WHOLLY INSIDE A LARGER ONE (Kentland inside
    Iroquois, Van Bibber Lake inside Little Walnut, Je-To Lake inside West
    Central), because a property can belong to two districts set up for
    different purposes; six more pairs touch along slivers. So districts
    overlap, and the card lists every district the map puts a point in.

ONE DATE IS NOT SHOWN, AND THE TABLE SAYS WHY (DATE_NOT_SHOWN). Ben Davis
(id 2) carries an establishment date of 10 May 1905, which cannot be the
day a conservancy district was established, because the act creating them
passed in 1947. The district is older than its form, most likely an earlier
sanitary body reorganised under the act, but that is inferred, so the card
prints no date for it rather than a wrong one. Any other date before 1947
stops the build, and so does the entry once the map stops carrying it.

THE COUNT IS PER COURT. The map's `circuit_county_court` names the county
whose circuit court set the district up; a district can reach into other
counties. The 100 districts come from 47 courts, and the agreement test is
run over each court's districts. A petition is filed "in the circuit court of
the county having the most land in the proposed district" (the department's
page), so the build checks that every district's court county holds some of
its land: districts grow after they are set up, and six now hold less of their
land in their court's county than in another, which proves nothing, but one
holds none at all.

ONE COURT IS NOT SHOWN, AND THE TABLE SAYS WHY (COURT_NOT_SHOWN). The map
files Nature Works (id 96) under the Noble County court, but draws it wholly
inside Porter County, and the department's 2026 directory lists the district
under Porter. The map's court is therefore wrong, and the right one would be
inferred, so the card names no court for it; its agreement test runs under
Porter, the county the map draws it in. The field the card reads is `court`;
the field the checks group by is `county`, and the two differ only there.

THE WEBSITE IS AS THE MAP PUBLISHES IT, with a scheme added where it has
none (http, which a server can move on to https), and WEBSITE_FIXES lists
every address measured on 2026-10-16 to reach nobody (ten names with no DNS
record) or to land somewhere other than the district (three), with what the
field carries instead. All 64 addresses the map and the directory give were
read that day: 48 answered, and an address that could not be read from here
for another reason (a reset connection, a robots.txt answering 202 or 503, a
403) stays, because that says nothing about whether a reader can reach it. The
department's 2026 directory is newer than the map's addresses, so the card
prefers the directory's address, carried in the directors file. The field is
named `url`, so the monthly link check treats it as a published link rather
than one this project chose.

PUBLISHING GAPS, recorded as evidence for the state-publishing ask (gap
in-conservancy-district-records): the layer and its item carry no licence or
terms of use; two records carry no status; one date predates the law; one
district is filed under a court whose county holds none of its land; three
districts are split across duplicate records; thirteen of the map's 35
website addresses reach nobody or the wrong place; and the directory that
names the boards gives four districts another district's id (listed in the
directors builder), so the map and the directory cannot be joined without a
table of corrections.
"""

import datetime
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))

import published_district_layers as psb  # noqa: E402

LAYER = ("https://gisdata.in.gov/server/rest/services/Hosted/"
         "Conservancy_Districts_of_Indiana_20250528/FeatureServer/54")
WHERE = "status='Active'"

# The Indiana Conservancy District Act passed in 1947, so no conservancy
# district was established before it.
ACT_YEAR = 1947

# id -> (the court county the map carries, the county the district is drawn
# in, why the card names no court)
COURT_NOT_SHOWN = {
    96: ("Noble", "Porter",
         "Nature Works: the map draws it wholly inside Porter County and the 2026 "
         "directory lists it under Porter, so the map's Noble County court is wrong"),
}

COUNTIES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                             "data", "app", "state-counties.json")

# id -> (the date the map carries, why the card prints none)
DATE_NOT_SHOWN = {
    2: ("1905-05-10", "Ben Davis: the map's date is 42 years before the act that "
        "creates conservancy districts, so it is not the day this district was "
        "established as one"),
}

# id -> (the address the map carries, what the card links instead or None, why).
# Each was measured on 2026-10-16; an entry whose map address has changed stops
# the build so it is re-read rather than left applying to nothing. A domain with
# no DNS record reaches nobody and can be registered again by anyone, so it is
# never linked. Where the department's 2026 directory gives a working address,
# the card links that one from the directors file instead (and prefers it over
# the map's address everywhere), so these entries only decide what the map's
# own field carries.
WEBSITE_FIXES = {
    2: ("www.bendavisconservancydistrict.com", None,
        "no DNS record for the name, with or without www"),
    39: ("www.ihcd219.com", None,
         "no DNS record; the 2026 directory gives ihcd-in.com"),
    55: ("www.vlacd.org", None,
         "no DNS record for the www name; the 2026 directory gives vlacd.org"),
    60: ("www.battleground.in.gov/water/", None,
         "redirects to the town of Battle Ground's home page, not the district's; "
         "the 2026 directory gives water.battleground.in.gov"),
    73: ("www.ourhartlake.com", None, "no DNS record for the name, with or without www"),
    78: ("www.basslakeconservancydistrict.com", None,
         "no DNS record; the 2026 directory gives basslakecd.in.gov"),
    79: ("www.lake-holiday.net", None, "no DNS record for the name, with or without www"),
    85: ("www.newparis.net/our-community", None,
         "redirects to a page on newparisindiana.com that answers 404; the 2026 "
         "directory gives newparisconservancydistrict.com"),
    96: ("www.ci.valparaiso.in.us", None,
         "the City of Valparaiso's home page, not the district's; the 2026 "
         "directory gives natureworks.myruralwater.com"),
    104: ("www.fishlakedistrict.net", None, "no DNS record for the name, with or without www"),
    112: ("www.damonrunconservancy.com", None,
          "the name has no address record, with or without www"),
    122: ("www.swlakemaxcd.com", None, "no DNS record for the name, with or without www"),
    125: ("www.graybrooklake.org", None, "no DNS record for the name, with or without www"),
}

# The map's district names are short ("Ben Davis", "Prairie Creek - Daviess").
# A name that already says what it is keeps its own words; these two are the
# map's abbreviations spelled out, and anything else gains "Conservancy
# District".
NAME_SPELLED_OUT = {
    "James Phillips CD": "James Phillips Conservancy District",
    "West Vigo Levee Assoc.": "West Vigo Levee Association Conservancy District",
}


def tidy(text):
    return " ".join(str(text).split()) if text is not None else ""


def district_name(raw):
    name = tidy(raw)
    if name in NAME_SPELLED_OUT:
        return NAME_SPELLED_OUT[name]
    if name.lower().endswith("conservancy district"):
        return name
    return name + " Conservancy District"


def established(props, key):
    ms = props.get("establishment_date")
    if ms is None:
        return None
    day = (datetime.datetime(1970, 1, 1) + datetime.timedelta(milliseconds=ms)).date()
    iso = day.isoformat()
    held = DATE_NOT_SHOWN.get(int(key))
    if held is not None:
        if held[0] != iso:
            psb.fail(SPEC, "district %s now carries the date %s, not the %s DATE_NOT_SHOWN "
                     "holds back; read it again" % (key, iso, held[0]))
        return None
    if day.year < ACT_YEAR:
        psb.fail(SPEC, "district %s carries the date %s, before the %d act that creates "
                 "conservancy districts" % (key, iso, ACT_YEAR))
    if day > datetime.date.today():
        psb.fail(SPEC, "district %s carries the date %s, after today" % (key, iso))
    return iso


def website(props, key):
    raw = tidy(props.get("cd_website"))
    fix = WEBSITE_FIXES.get(int(key))
    if fix is not None:
        if fix[0] != raw:
            psb.fail(SPEC, "district %s's website on the map is now %r, not the %r "
                     "WEBSITE_FIXES replaces; read it again" % (key, raw, fix[0]))
        return fix[1]
    if not raw:
        return None
    if " " in raw:
        psb.fail(SPEC, "district %s's website %r is not an address" % (key, raw))
    if not raw.lower().startswith(("http://", "https://")):
        raw = "http://" + raw
    return raw


def read(props):
    if (props.get("status") or "").strip() != "Active":
        psb.fail(SPEC, "a record that is not active came through the filter: %r" % props)
    ident = props.get("id_number")
    if not isinstance(ident, int) or ident <= 0:
        psb.fail(SPEC, "id_number %r is not a positive whole number: %r" % (ident, props))
    key = str(ident)
    court = tidy(props.get("circuit_county_court"))
    out = {
        "key": key,
        "county": court,
        "court": court,
        "label": district_name(props.get("conservancy_district_name")),
    }
    held = COURT_NOT_SHOWN.get(ident)
    if held is not None:
        if held[0] != court:
            psb.fail(SPEC, "district %s's court on the map is now %r, not the %r "
                     "COURT_NOT_SHOWN holds back; read it again" % (key, court, held[0]))
        out["county"] = held[1]
        del out["court"]
    purposes = tidy(props.get("purposes")).rstrip(",")
    if purposes:
        out["purposes"] = purposes
    est = established(props, key)
    if est:
        out["est"] = est
    url = website(props, key)
    if url:
        out["url"] = url
    return out


def ring_points(geometry):
    polys = ([geometry["coordinates"]] if geometry["type"] == "Polygon"
             else geometry["coordinates"])
    for poly in polys:
        for x, y in poly[0]:
            yield x, y


def in_ring(x, y, ring):
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def in_geometry(x, y, geometry):
    polys = ([geometry["coordinates"]] if geometry["type"] == "Polygon"
             else geometry["coordinates"])
    for poly in polys:
        if in_ring(x, y, poly[0]) and not any(in_ring(x, y, hole) for hole in poly[1:]):
            return True
    return False


def court_county_holds_land(feats):
    """Every district's court county holds some of its land: at least one of
    the district's drawn vertices lies inside that county on the shipped county
    file. COURT_NOT_SHOWN's district must hold none in the county the map names
    and some in the county the table names, or the entry is out of date."""
    with open(COUNTIES_FILE, encoding="utf-8") as fh:
        counties = {f["properties"]["BASENAME"]: f["geometry"]
                    for f in json.load(fh)["features"]}

    def touches(geometry, county):
        shape = counties.get(county)
        if shape is None:
            psb.fail(SPEC, "no county named %r in %s" % (county, COUNTIES_FILE))
        return any(in_geometry(x, y, shape) for x, y in ring_points(geometry))

    for f in feats:
        p = f["properties"]
        held = COURT_NOT_SHOWN.get(int(p["key"]))
        if held is not None:
            if touches(f["geometry"], held[0]):
                psb.fail(SPEC, "district %s now reaches %s County, so COURT_NOT_SHOWN's "
                         "reason no longer holds; read it again" % (p["key"], held[0]))
            if not touches(f["geometry"], held[1]):
                psb.fail(SPEC, "district %s is no longer drawn in %s County; read "
                         "COURT_NOT_SHOWN again" % (p["key"], held[1]))
        elif not touches(f["geometry"], p["court"]):
            psb.fail(SPEC, "district %s (%s) holds none of its land in %s County, "
                     "whose court the map says set it up" % (p["key"], p["label"], p["court"]))


def every_table_entry_used(feats):
    court_county_holds_land(feats)
    keys = {f["properties"]["key"] for f in feats}
    for table, name in ((DATE_NOT_SHOWN, "DATE_NOT_SHOWN"), (WEBSITE_FIXES, "WEBSITE_FIXES"),
                        (COURT_NOT_SHOWN, "COURT_NOT_SHOWN")):
        unused = sorted(k for k in table if str(k) not in keys)
        if unused:
            psb.fail(SPEC, "%s names district(s) %s, which the map no longer draws as active"
                     % (name, ", ".join(str(k) for k in unused)))
    names = {f["properties"]["label"] for f in feats}
    unused = sorted(v for v in NAME_SPELLED_OUT.values() if v not in names)
    if unused:
        psb.fail(SPEC, "NAME_SPELLED_OUT spells out %s, which no district now carries"
                 % ", ".join(unused))


SPEC = psb.Spec(
    tag="in",
    label="build_in_conservancy_districts",
    layer=LAYER,
    user_agent="districtry/1.0 (+https://districtry.com/in/)",
    out_fields=("id_number,conservancy_district_name,status,establishment_date,"
                "circuit_county_court,purposes,cd_website"),
    expect=100,
    expect_groups=47,
    read=read,
    out_file="in-conservancy-districts.json",
    group="county",
    group_nouns=("court", "courts"),
    card_noun="conservancy district card",
    interval="4",
    pace=2.0,
    where=WHERE,
    measure_field="SHAPE__Area",
    multipart_records=3,
    extra_check=every_table_entry_used,
    card_claims=(
        "Department of Natural Resources' map of conservancy districts",
        "elected by the property owners in the district",
    ),
    inside=(
        # inside Lake Lemon Conservancy District (court: Brown), measured on
        # the 2026-10-16 fetch
        (-86.3977, 39.2560, "95", "Lake Lemon Conservancy District"),
        # Kentland lies wholly inside Iroquois, so a point in both is checked
        # by the card's list rather than here, where one district is wanted
    ),
    outside=(
        # Monument Circle, Indianapolis: in no district on the 2026-10-16 fetch
        (-86.15807, 39.76838, "Monument Circle, Indianapolis"),
    ),
)

if __name__ == "__main__":
    psb.main(SPEC, __doc__)
