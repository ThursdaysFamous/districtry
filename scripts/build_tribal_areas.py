#!/usr/bin/env python3
"""Build one state's tribal-land boundary file, from the two files that already own the facts.

Three publishers and one join answer this layer, and each is read in exactly one
place:

  the land          `scripts/tribal_areas.py`              Census AIANNHA
  land -> government `data/tribal-government-join.json`     this project's join
  the government    `data/bia-tribal-governments.json`      BIA leaders directory
  districts on it   the Census's Tribal Subdivisions layer, measured per build

THE FIRST DRAFT OF THIS FILE CARRIED ITS OWN GOVERNMENT TABLE, which was a
second copy of the join -- the defect this repository records over and over --
and it is worth saying why that was easy to do: the join and the Bureau reader
had landed days earlier for a different step of the same plan, and nothing in
the layer's own vicinity pointed at them. It also guessed Illinois's AIANNH code
as 2585, where the Census answers 2980, and that was caught only because the
table check refused to ship an area it could not name. SEARCH THE TREE FOR THE
FACT BEFORE WRITING A TABLE OF IT.

WHAT THE CARD MAY SAY, AND WHAT IT MAY NOT
------------------------------------------
Everything on the card comes from one of the four rows above. Three claims were
nearly written from memory instead, and all three were wrong or unsourced:

  the nation's name   the join's `government`, which `validate_tribal_join.py`
                      holds to the Bureau's own list. Note that this is NOT the
                      Census's NAME field: the Census writes "Prairie Band of
                      Potawatomi Nation Off-Reservation Trust Land", which is a
                      description of a parcel, and the government calls itself
                      the Prairie Band Potawatomi Nation.
  the seat            the Bureau's `city` + `state` columns. A first draft wrote
                      "Mayetta, Kansas" from memory; it happens to be right, and
                      a geographic claim about a place gets a source before it is
                      written down, not after.
  the nation's site   the Bureau's `website` column, published as http. It is
                      LINKED and never fetched.
  how the council
  is chosen           NOT STATED, because nothing readable says. A first draft
                      asserted that the council is elected by the nation's
                      members at large. That may well be so and this project has
                      no source for it, and an invented mechanism is the same
                      class of error as an invented name.

What the layer CAN say about districts it measures: the Census publishes 484
tribal subdivisions nationwide (the positive control), and whether any of them
falls on a given state's tribal land is a question with an answer. For Illinois
on 2026-10-01 the answer is none, and the nation publishes none anywhere, so "no
district is drawn on this land" is a measurement rather than a guess.

WHY NO COUNCIL MEMBER IS NAMED
------------------------------
An officeholder is never guessed, and where no verifiable roster exists the card
links the official body. The Bureau's directory carries exactly ONE person per
government -- a leader, not a council -- and that reader deliberately drops the
person columns, so there is no federal shortcut. The authority is each nation's
own published council, and for Illinois this project cannot read it:
pbpindiantribe.com answers robots.txt and its own front page with HTTP 403
carrying Cloudflare's "Just a moment..." interstitial, three reads sixteen
seconds apart on 2026-10-01, asked with the roster-bot token that would have
done the crawling. A managed challenge is an access control and is never solved
or worked around, and no second client was tried, because escalating past one is
working around it. The host is recorded in
`robots_policy.CHALLENGE_FRONTED_HOSTS` so the fleet's shared reader refuses it
instead of reading its 403 as "no policy published, therefore allowed", which is
what it did before -- publishing a permission the host has never granted.

So the card names the nation, says where its government sits, says no district
is drawn here, links the nation, and names nobody. That is the shape Iowa
already ships for a residency district elected countywide: draw the ground, say
how the seat is filled, name no person on it.

WHY AN UNPOPULATED PARCEL IS DRAWN
----------------------------------
Nobody lived on Illinois's parcel at the 2020 census, and the generic rule for a
body not elected from the ground it covers is roster rows rather than a polygon.
Adam ruled on 2026-09-30 that this parcel is drawn anyway, and the reason holds:
a government answers for that ground, so a reader who clicks it should be told
which one. A layer that drew only inhabited land would answer "no government
here" over land a nation governs.

Usage:
    python3 scripts/build_tribal_areas.py --selftest        # offline
    python3 scripts/build_tribal_areas.py --check           # offline, shipped files
    python3 scripts/build_tribal_areas.py --state Illinois --tag il
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tribal_areas as T  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JOIN = os.path.join(REPO, "data", "tribal-government-join.json")
BIA = os.path.join(REPO, "data", "bia-tribal-governments.json")

# The fields the Tribal Subdivisions layer carries. It has no POP100, which is
# why the shared AREA_FIELDS gets a 400 back from it -- an error envelope that
# `tribal_areas._require_no_error` raises on rather than reading as "no
# subdivisions here", which is the measurement this whole module would otherwise
# have got wrong in the confident direction.
SUBDIVISION_FIELDS = "AIANNH,NAME,BASENAME,GEOID,AREALAND"

# THE CURRENT VINTAGE CARRIES NO POPULATION AT ALL, measured 2026-10-01: POP100
# is null on 0 of 312 reservations and 0 of 177 trust lands there, while the
# Census 2020 vintage carries it on every one of its 312 and 167. So a count
# comes from the 2020 vintage, joined on AIANNH, and the geometry still comes
# from the current one.
#
# AND THE KEY IS (AIANNH, LAND CLASS), NEVER AIANNH ALONE. A reservation and its
# off-reservation trust land SHARE one area code -- the join's own note says so --
# so a count joined on the code attributes the whole nation's reservation
# population to whichever parcel is being described. The first version of this
# function did exactly that and credited Illinois's half-square-kilometre parcel
# with the 1,529 people the Census counted on the nation's Kansas reservation,
# which is the same false-statement-about-a-place this comment block was written
# to prevent, two paragraphs further down. A pair matching more than one 2020
# feature is reported as not attributable rather than summed, because several
# parcels under one code can sit in several states.
#
# READING THAT NULL AS A ZERO IS A FALSE STATEMENT ABOUT A PLACE, and this
# project had already made it: `il/data/app/coverage-gaps.json` told readers that
# "the last census counted nobody living on" the Illinois parcel. It did not
# count it at all. The parcel is one of THIRTEEN trust lands whose AIANNH code
# is in the current vintage and not in the 2020 one, so no census population for
# it exists to publish. The control that settles it is the same nation's Kansas
# reservation, which also reports null on the current vintage and 1,529 people on
# the 2020 one -- an inhabited reservation, so the null was never a count.
POP_VINTAGE = "Census 2020"

# Why this project cannot name a nation's council, per nation, keyed on the
# Census's AIANNH code. NOTHING PUBLISHES THIS, so it is the one declaration here
# rather than a read: each entry is a measurement of a named host on a named day,
# and `check` refuses to ship an area that names nobody and explains nothing.
# An entry leaves by the council becoming readable, never by being deleted.
ROSTER_BLOCKED = {
    "1410": {
        "host": "hannahville.net",
        "measured": "2026-10-01",
        "why": "The nation's own site is the authority for its council, and that "
               "host is recorded as answering some requests with a managed "
               "challenge and others normally (challenged 3 of 6 reads across "
               "two clients, measured 2026-09-29). Getting in on the reads where "
               "a control happens to be off is working around it, so no name is "
               "carried and the card links the nation instead.",
    },
    "1880": {
        "host": "kbic-nsn.gov",
        "measured": "2026-10-01",
        "why": "The nation's own site is the authority for its council, and that "
               "host is recorded as answering some requests with a managed "
               "challenge (measured 2026-09-29). An access control is not worked "
               "around, so no name is carried and the card links the nation.",
    },
    "1960": {
        "host": "lrboi-nsn.gov",
        "measured": "2026-10-01",
        "why": "The nation publishes its council list to its own members only: "
               "both of the paths its front page gives for the Tribal Council "
               "answer HTTP 200 at /member-only-error, measured 2026-10-01. That "
               "is the nation's own decision about its own roll, so no name is "
               "carried and the card links the nation.",
    },
    "2580": {
        "host": "kbic-nsn.gov",
        "measured": "2026-10-01",
        "why": "The Ontonagon Reservation is held by the same government as the "
               "L'Anse Reservation, whose own site is recorded as answering some "
               "requests with a managed challenge (measured 2026-09-29). An "
               "access control is not worked around, so no name is carried and "
               "the card links the nation.",
    },
    "2980": {
        "host": "pbpindiantribe.com",
        "measured": "2026-10-01",
        "why": "The nation publishes its council on its own site, which answers "
               "every request from this project with a Cloudflare challenge — "
               "robots.txt and the front page alike, HTTP 403, three reads "
               "sixteen seconds apart. An access control is not worked around, "
               "so no name is carried and the card links the nation instead.",
    },
}

# Where a nation publishes its own council, for the nations whose page answers
# this project and whose names are NOT YET CARRIED. This is a different fact
# from ROSTER_BLOCKED above: nothing stops the read, the work has not been done.
# Each entry is a dated measurement of a named page -- robots.txt read with the
# same client, then the page itself, HTTP 200 with a body -- so the card states
# where a reader can find the names today and the remaining work is visible per
# nation instead of reading as twenty silent absences. An entry leaves by the
# names being carried, never by being deleted.
#
# WHY THE SENTENCE IS BUILT HERE AND NOT IN THE APP: the app has no way to tell
# a council nobody can read from one nobody has read, and a card that guessed
# between them would be making a claim about this project rather than reporting
# a measurement.
ROSTER_NOT_READ = {
    # Empty since 2026-10-06, when all nineteen nations that were here had their
    # councils read by scripts/tribal_council_scraper.py. The table stays for
    # the next state whose nations publish a council nobody has read yet.
}


def _not_read_why(entry):
    """The card's own words for a council this project has not read yet."""
    return ("Not carried yet. The nation publishes its council at %s, which "
            "answered this project on %s; these names are not in this app yet, "
            "so the card links the nation instead of naming anybody."
            % (entry["page"], entry["measured"]))


COUNCILS = os.path.join(REPO, "data", "tribal-councils.json")

# The order a council is listed in on the card: the head of the government,
# then the deputy, then the other officers, then everyone else, each group in
# the order the nation's own page gives. Two pages list their council in
# PHOTO order (Menominee's and Forest County Potawatomi's captions read left to
# right), which is no order a reader can use.
_OFFICE_RANK = [
    (r"^(?:tribal )?(?:chair(?:man|woman|person)?|president|chief)$", 0),
    (r"^vice[- ]|^sub-chief$", 1),
    (r"legislative leader", 2),
    (r"secretary|treasurer", 3),
    (r"sergeant|chaplain|elder", 4),
]


def _office_rank(role):
    low = role.lower()
    for pat, rank in _OFFICE_RANK:
        if re.search(pat, low):
            return rank
    return 5


def load_councils():
    if not os.path.exists(COUNCILS):
        return {}
    return json.load(open(COUNCILS))["councils"]


def _roster_note(rec):
    """The card's own sentence for where the names came from and when."""
    when = rec.get("carriedFrom") or rec["read"]
    if rec["source"] == "state-list":
        return ("Named by the %s's list of Wisconsin tribal officials, updated %s, "
                "because the nation publishes no council of its own. Read %s."
                % (rec["publisher"], rec["listUpdated"], when))
    if rec.get("carriedFrom"):
        return ("From the nation's own council page, last read %s; the page could "
                "not be read on the most recent weekly run." % when)
    return "From the nation's own council page, read %s." % when


def roster_props(code, councils):
    """The roster fields a feature carries, or None when no council is carried."""
    rec = councils.get(code)
    if rec is None:
        return None
    members = sorted(rec["members"], key=lambda m: _office_rank(m["role"]))
    return {
        "roster": members,
        "rosterWhy": None,
        "rosterNote": _roster_note(rec),
        "rosterSource": rec["source"],
        "rosterPage": rec["page"],
        "rosterRead": rec.get("carriedFrom") or rec["read"],
        "rosterHost": None,
        "rosterMeasured": None,
    }


def load_join():
    return json.load(open(JOIN))


def load_bia():
    """The Bureau's governments, keyed by the name the join uses."""
    doc = json.load(open(BIA))
    return {g["name"]: g for g in doc["governments"]}


def _state_areas(state_name):
    """Every governed tribal area with ground inside one state, measured."""
    resolved = T.resolve_layers()
    T.check_vintage_counts(resolved)
    state_feat, state_code = T.state_polygon(state_name)
    out = []
    for cls in T.GOVERNED_CLASSES:
        for feat in T.fetch_layer(T.AIANNHA, resolved[T.DEFAULT_VINTAGE][cls],
                                  fields=T.AREA_FIELDS):
            clip = T.clip_to_state(feat["geometry"], state_feat["geometry"])
            if clip["keep"]:
                out.append((cls, feat, clip))
    return out, state_code, state_feat, resolved


def census_population(resolved):
    """The 2020 count per AIANNH code, and which codes the 2020 geography lacks.

    Returns `(counts, known_codes)`. A code in `known_codes` with no entry in
    `counts` is a real zero; a code absent from `known_codes` was not in the 2020
    tabulation geography at all, and those are two different statements a card
    must not merge. The control is the count itself: a vintage that answers with
    no populations anywhere cannot settle anything, so that raises.
    """
    counts, known, seen = {}, set(), {}
    for cls in T.GOVERNED_CLASSES:
        layer = resolved[POP_VINTAGE].get(cls)
        if layer is None:
            continue
        for feat in T.fetch_layer(T.AIANNHA, layer, fields="AIANNH,NAME,POP100"):
            props = feat["properties"]
            key = (str(props.get("AIANNH")), cls)
            known.add(key)
            seen[key] = seen.get(key, 0) + 1
            if props.get("POP100") is not None:
                counts[key] = props["POP100"]
    # A pair that matched several features cannot be attributed to one parcel.
    for key, n in seen.items():
        if n > 1:
            counts.pop(key, None)
    if not counts:
        raise RuntimeError(
            "control failed: the %s vintage answered with no population on any "
            "feature, so it cannot settle whether a parcel was counted"
            % POP_VINTAGE)
    print("build-tribal-areas: population control — %s carries one attributable "
          "count for %d of %d (code, class) pair(s); %d pair(s) hold several "
          "parcels and are not attributed"
          % (POP_VINTAGE, len(counts), len(known),
             sum(1 for n in seen.values() if n > 1)))
    return counts, known


def districts_on(state_feat, subdivision_layer):
    """Which tribal subdivisions have ground in this state, with a control.

    A subdivision IS a district a nation draws on its own land, so an empty
    answer here is the claim "no district is drawn on this ground" -- which is
    only worth anything beside a control proving the query finds subdivisions
    where they exist. The nationwide count is that control, and a zero from it
    raises rather than reading as a quiet confirmation.
    """
    everywhere = T.fetch_layer(T.AIANNHA, subdivision_layer, fields=SUBDIVISION_FIELDS)
    if not everywhere:
        raise RuntimeError(
            "control failed: the Tribal Subdivisions layer answered with no "
            "features at all, so an empty result for this state says nothing")
    here = {}
    for feat in everywhere:
        clip = T.clip_to_state(feat["geometry"], state_feat["geometry"])
        if clip["inside_km2"] > 0:
            here.setdefault(str(feat["properties"].get("AIANNH")), []).append(
                feat["properties"].get("NAME"))
    nations = {str(f["properties"].get("AIANNH")) for f in everywhere}
    print("build-tribal-areas: subdivision control — %d nationwide across %d "
          "nation(s); %d with ground in this state"
          % (len(everywhere), len(nations), sum(len(v) for v in here.values())))
    return here, len(everywhere)


def check_join(areas, join, bia):
    """Hold the shipped areas, the join and the Bureau's list to one another.

    Three ways to fail, each a different wrong card. An area the join does not
    name would render a parcel description and no government. A join entry naming
    a government the Bureau does not list would name a body no publisher
    recognises. And a government with no seat is a card that cannot say where the
    people who answer for this land actually sit.
    """
    for _, feat, _ in areas:
        code = str(feat["properties"].get("AIANNH"))
        entry = join["areas"].get(code)
        if entry is None:
            raise RuntimeError(
                "AIANNH %s has ground here and data/tribal-government-join.json "
                "does not name its government — add the join entry rather than a "
                "table in this file" % code)
        gov = bia.get(entry["government"])
        if gov is None:
            raise RuntimeError(
                "the join names %r for AIANNH %s and the Bureau's own list does "
                "not carry that government" % (entry["government"], code))
        if not gov.get("state"):
            raise RuntimeError("the Bureau lists no state for %r, so no card can "
                               "say where it sits" % entry["government"])
    return True


def _seat(gov):
    """Where a government sits, from the Bureau's own two columns.

    The city alone is ambiguous and the state alone is vague, so both are used
    where both exist and the state alone is the honest fallback — never a city
    this project supplied.
    """
    if gov.get("city") and gov.get("state"):
        return "%s, %s" % (gov["city"], gov["state"])
    return gov.get("state") or None


def _population_note(counts, known, code, cls):
    """What the Census says lives on this parcel, in the card's own words."""
    if (code, cls) not in known:
        return ("Not counted. This land was added to the Census's map after the "
                "2020 count, so no census population for it has been published.")
    people = counts.get((code, cls))
    if people is None:
        return ("Not published. The Census counted this land in 2020 and gives "
                "no population for it.")
    if people == 0:
        return "Nobody lived here at the 2020 census."
    return "{:,} people at the 2020 census.".format(people)


def _districts_note(district_names):
    """Whether any district is drawn on this land, in the card's own words."""
    if not district_names:
        return ("None. The Census draws no tribal district on this land, so no "
                "council seat belongs to it.")
    return ", ".join(sorted(district_names))


def _record(cls, feat, clip, entry, gov, district_names, counts, known, councils=None):
    props = feat["properties"]
    code = str(props.get("AIANNH"))
    rec = {
        "type": "Feature",
        "geometry": feat["geometry"],
        "properties": {
            "aiannh": code,
            # The Census's own text for the parcel, kept so a reader who looks
            # the land up finds the same words, and never used as the name of
            # the government.
            "censusName": props.get("NAME"),
            "landClass": cls,
            "nation": entry["government"],
            "parentNation": entry.get("parentGovernment"),
            "seat": _seat(gov),
            "url": gov.get("website"),
            # Measured per build: the districts a nation draws on its own land.
            # An empty list means none was found beside a control that found
            # 484 nationwide, which is a measurement and not a silence.
            "districts": sorted(district_names),
            # The 2020 count, or None when the parcel was not in the 2020
            # tabulation geography — which `countedIn2020` distinguishes, so a
            # card can never print "nobody lives here" over land the census
            # never counted.
            "population": counts.get((code, cls)) if (code, cls) in known else None,
            "countedIn2020": (code, cls) in known,
            # THE TWO SENTENCES THE CARD PRINTS, written here because the
            # measurement is here. The app has no way to tell a null population
            # apart from a zero, or an empty district list apart from a district
            # list nobody looked for, so a card that re-derived either from the
            # raw fields would be guessing at what this builder measured. The
            # raw values stay beside them for anything that wants to compute.
            "populationNote": _population_note(counts, known, code, cls),
            "districtsNote": _districts_note(district_names),
            "areaKm2": round(clip["inside_km2"], 4),
            "wholeAreaKm2": round(clip["whole_km2"], 4),
            "shareInState": round(clip["share"], 6),
        },
    }
    return stamp(rec, councils or {})


def _no_roster_props(code, councils):
    """The roster fields the GEOMETRY file carries. For a nation whose council
    is carried they are all empty, because the names live in the instance's
    own tribal-councils.json: the geometry is served cache-first and changes
    about once a decade, while a council changes whenever an election or an
    appointment does, and a name written into a cache-first file would reach a
    returning reader only after the next cache bump. For any other nation they
    say why the card names nobody, from whichever of the two tables above
    describes it: a measured refusal, or a page that answers and has not been
    read yet. Never both, which `check` enforces."""
    if code in councils:
        return {"roster": None, "rosterWhy": None, "rosterHost": None,
                "rosterMeasured": None}
    blocked = ROSTER_BLOCKED.get(code)
    not_read = ROSTER_NOT_READ.get(code)
    out = {
        "roster": None,
        "rosterWhy": (blocked["why"] if blocked
                      else _not_read_why(not_read) if not_read else None),
        "rosterHost": (blocked or not_read or {}).get("host"),
        "rosterMeasured": (blocked or not_read or {}).get("measured"),
    }
    # Only a page that answers and has not been read has an address to give.
    if not_read:
        out["rosterPage"] = not_read["page"]
    return out


def stamp(feature, councils):
    """Set a geometry feature's roster fields. The one place they are written,
    so a rebuild of the land and a weekly re-read of the councils cannot write
    them two ways."""
    p = feature["properties"]
    for k in [k for k in p if k.startswith("roster")]:
        del p[k]
    p.update(_no_roster_props(p["aiannh"], councils))
    return feature


def _councils_path(tag):
    return os.path.join(REPO, tag, "data", "app", "tribal-councils.json")


def instance_councils(doc, councils):
    """What one instance's tribal-councils.json holds: the council of every
    nation it ships whose council is carried, already in card order."""
    out = {}
    for f in doc["features"]:
        want = roster_props(f["properties"]["aiannh"], councils)
        if want is not None:
            out[f["properties"]["aiannh"]] = want
    return {"note": ("Tribal councils, keyed by the Census AIANNH code of the "
                     "land each nation governs. Generated by "
                     "scripts/build_tribal_areas.py --rosters from "
                     "data/tribal-councils.json; never edit by hand."),
            "councils": dict(sorted(out.items()))}


def _write_json(path, doc):
    with open(path, "w") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")


def stamp_rosters():
    """Offline: write each instance's tribal-councils.json from the councils
    file, and re-stamp its geometry's roster fields. The geometry moves only
    when a nation's council starts or stops being carried; a weekly re-read
    that changes a name changes the councils file alone."""
    councils = load_councils()
    n = 0
    for tag in sorted(os.listdir(REPO)):
        path = os.path.join(REPO, tag, "data", "app", "tribal-areas.json")
        if not os.path.exists(path):
            continue
        doc = json.load(open(path))
        for f in doc["features"]:
            stamp(f, councils)
        with open(path, "w") as fh:
            json.dump(doc, fh)
            fh.write("\n")
        mine = instance_councils(doc, councils)
        cpath = _councils_path(tag)
        if mine["councils"]:
            _write_json(cpath, mine)
        elif os.path.exists(cpath):
            os.remove(cpath)
        for f in doc["features"]:
            p = f["properties"]
            c = mine["councils"].get(p["aiannh"])
            print("build-tribal-areas --rosters: %s %s %s — %s"
                  % (tag, p["aiannh"], p["nation"],
                     "%d named" % len(c["roster"]) if c else "nobody named"))
        n += 1
    print("build-tribal-areas --rosters: OK — %d instance file(s) stamped" % n)


def build(state_name, tag, out_path=None):
    join, bia = load_join(), load_bia()
    areas, state_code, state_feat, resolved = _state_areas(state_name)
    check_join(areas, join, bia)
    here, _ = districts_on(state_feat, resolved[T.DEFAULT_VINTAGE]["subdivision"])
    counts, known = census_population(resolved)
    feats = []
    for cls, feat, clip in areas:
        code = str(feat["properties"].get("AIANNH"))
        entry = join["areas"][code]
        feats.append(_record(cls, feat, clip, entry, bia[entry["government"]],
                             here.get(code, []), counts, known, load_councils()))
    feats.sort(key=lambda f: (f["properties"]["nation"], f["properties"]["aiannh"]))
    doc = {
        "type": "FeatureCollection",
        "state": state_name,
        "stateCode": state_code,
        "source": "US Census Bureau TIGERweb AIANNHA, current vintage",
        "governmentSource": json.load(open(BIA))["source"],
        "features": feats,
    }
    path = out_path or os.path.join(REPO, tag, "data", "app", "tribal-areas.json")
    with open(path, "w") as fh:
        json.dump(doc, fh)
        fh.write("\n")
    if out_path is None:
        mine = instance_councils(doc, load_councils())
        if mine["councils"]:
            _write_json(_councils_path(tag), mine)
    for f in feats:
        p = f["properties"]
        print("build-tribal-areas: %s — %s, seat %s, %s, %.4f km2, %s resident(s), "
              "%d district(s) drawn, council %s"
              % (tag, p["nation"], p["seat"], p["landClass"], p["areaKm2"],
                 p["population"], len(p["districts"]),
                 "carried" if p["aiannh"] in load_councils() else "not carried"))
    print("build-tribal-areas: OK — %s wrote %d area(s) in %s (state code %s)"
          % (tag, len(feats), state_name, state_code))
    return doc


def check():
    """Offline: every shipped file against the join, the Bureau's list, the
    councils file and itself."""
    join, bia = load_join(), load_bia()
    councils = load_councils()
    seen = areas = 0
    for tag in sorted(os.listdir(REPO)):
        path = os.path.join(REPO, tag, "data", "app", "tribal-areas.json")
        if not os.path.exists(path):
            continue
        seen += 1
        doc = json.load(open(path))
        cpath = _councils_path(tag)
        shipped_councils = (json.load(open(cpath)) if os.path.exists(cpath)
                            else None)
        want_councils = instance_councils(doc, councils)
        if want_councils["councils"]:
            if shipped_councils != want_councils:
                raise RuntimeError(
                    "%s/data/app/tribal-councils.json differs from what "
                    "data/tribal-councils.json gives it — run "
                    "build_tribal_areas.py --rosters" % tag)
        elif shipped_councils is not None:
            raise RuntimeError(
                "%s ships tribal-councils.json and carries no council — remove "
                "it, or the app fetches a file that names nobody" % tag)
        carried = want_councils["councils"]
        if doc["state"] not in join["statesCovered"]:
            raise RuntimeError(
                "%s ships tribal areas for %s and the join does not list it as "
                "covered — re-run the join rather than the layer"
                % (tag, doc["state"]))
        for feat in doc["features"]:
            areas += 1
            # The geometry's own roster fields must be what `stamp` writes,
            # and the card reads them with the councils file merged over them,
            # so every check below is made on that merged view.
            geo = feat["properties"]
            stamped = _no_roster_props(geo["aiannh"], councils)
            if {k: v for k, v in geo.items() if k.startswith("roster")} != stamped:
                raise RuntimeError(
                    "%s: AIANNH %s's geometry carries roster fields `stamp` "
                    "would not write — run build_tribal_areas.py --rosters"
                    % (tag, geo["aiannh"]))
            p = dict(geo)
            p.update(carried.get(geo["aiannh"], {}))
            entry = join["areas"].get(p["aiannh"])
            if entry is None:
                raise RuntimeError("%s ships AIANNH %s, which the join does not "
                                   "name" % (tag, p["aiannh"]))
            if p["nation"] != entry["government"]:
                raise RuntimeError(
                    "%s names %r for AIANNH %s where the join says %r — rebuild "
                    "the file rather than editing it"
                    % (tag, p["nation"], p["aiannh"], entry["government"]))
            gov = bia.get(p["nation"])
            if gov is None:
                raise RuntimeError("%s names %r, which the Bureau's list does not "
                                   "carry" % (tag, p["nation"]))
            if p["seat"] != _seat(gov):
                raise RuntimeError(
                    "%s says %r sits at %r where the Bureau says %r"
                    % (tag, p["nation"], p["seat"], _seat(gov)))
            if p["url"] != gov.get("website"):
                raise RuntimeError("%s links %r for %r where the Bureau publishes "
                                   "%r" % (tag, p["url"], p["nation"],
                                           gov.get("website")))
            # A carried council must be exactly what the councils file says,
            # stamped by the one function that stamps it, so a weekly re-read
            # that forgot to re-stamp, or a hand edit, fails here.
            want = roster_props(p["aiannh"], councils)
            if want is not None:
                got = {k: p.get(k) for k in want}
                if got != want:
                    raise RuntimeError(
                        "%s: AIANNH %s carries a council that differs from "
                        "data/tribal-councils.json — run build_tribal_areas.py "
                        "--rosters" % (tag, p["aiannh"]))
                if p["aiannh"] in ROSTER_BLOCKED or p["aiannh"] in ROSTER_NOT_READ:
                    raise RuntimeError(
                        "%s: AIANNH %s names its council AND is recorded as unread "
                        "or blocked — retire the stale entry" % (tag, p["aiannh"]))
            elif p["roster"] is not None:
                raise RuntimeError("%s: AIANNH %s names people the councils file "
                                   "does not carry" % (tag, p["aiannh"]))
            # The one thing a card may never render is an unexplained absence.
            if p["roster"] is None and not p["rosterWhy"]:
                raise RuntimeError(
                    "%s: AIANNH %s names nobody and says why nowhere — add a "
                    "ROSTER_BLOCKED or ROSTER_NOT_READ entry with the host and "
                    "the date, or carry a roster" % (tag, p["aiannh"]))
            if (p["roster"] is None
                    and p["aiannh"] not in ROSTER_BLOCKED
                    and p["aiannh"] not in ROSTER_NOT_READ):
                raise RuntimeError(
                    "%s: AIANNH %s ships a reason this module does not declare, "
                    "so nothing re-reads it" % (tag, p["aiannh"]))
    if not seen:
        raise RuntimeError("no instance ships tribal-areas.json, so this gate "
                           "would pass vacuously")
    both = sorted(set(ROSTER_BLOCKED) & set(ROSTER_NOT_READ))
    if both:
        raise RuntimeError(
            "AIANNH %s is recorded as blocked AND as readable-but-not-read — a "
            "nation cannot be both, so one of the two measurements is stale"
            % ", ".join(both))
    shipped = {
        f["properties"]["aiannh"]
        for tag in os.listdir(REPO)
        for f in (json.load(open(os.path.join(REPO, tag, "data", "app",
                                              "tribal-areas.json")))["features"]
                  if os.path.exists(os.path.join(REPO, tag, "data", "app",
                                                 "tribal-areas.json")) else [])}
    orphans = sorted((set(ROSTER_BLOCKED) | set(ROSTER_NOT_READ) | set(councils))
                     - shipped)
    if orphans:
        raise RuntimeError(
            "a roster record or a council names AIANNH %s and no instance ships it — a "
            "measurement nothing reads is the shape this project keeps finding "
            "wrong" % ", ".join(orphans))
    print("build-tribal-areas --check: OK — %d instance(s), %d area(s); every "
          "government named by the join and listed by the Bureau, every seat and "
          "link theirs, %d council(s) carried as read, and every unnamed roster "
          "explained" % (seen, areas, len(councils)))
    return True


def selftest():
    """Offline. The three ways `check_join` fails, and the seat fallback."""
    def feat(code):
        return {"properties": {"AIANNH": code}}

    join = {"areas": {"2980": {"government": "Prairie Band Potawatomi Nation"}}}
    bia = {"Prairie Band Potawatomi Nation": {"name": "Prairie Band Potawatomi Nation",
                                              "city": "Mayetta", "state": "KS",
                                              "website": "http://example.invalid"}}
    assert check_join([("trust-land", feat("2980"), {})], join, bia) is True

    cases = [
        ("9999", join, bia, "does not name its government"),
        ("2980", {"areas": {"2980": {"government": "No Such Nation"}}}, bia,
         "own list does not carry"),
        ("2980", join, {"Prairie Band Potawatomi Nation": {"city": "Mayetta"}},
         "no state for"),
    ]
    for code, j, b, want in cases:
        try:
            check_join([("trust-land", feat(code), {})], j, b)
        except RuntimeError as e:
            assert want in str(e), (want, str(e))
        else:
            raise AssertionError("expected a failure containing %r" % want)

    # The seat is the Bureau's, and a missing city falls back to the state
    # rather than to a city this project supplied.
    assert _seat({"city": "Mayetta", "state": "KS"}) == "Mayetta, KS"
    assert _seat({"state": "KS"}) == "KS"
    assert _seat({"city": "Mayetta"}) is None
    assert _seat({}) is None

    # The four population branches are four different statements about a place,
    # and the one that matters most is the difference between a parcel the
    # census never counted and a parcel where it counted nobody.
    assert "added to the Census's map after" in _population_note({}, set(), "2980", "trust-land")
    assert _population_note({}, {("2980", "trust-land")}, "2980", "trust-land").startswith("Not published")
    assert _population_note({("2980", "trust-land"): 0}, {("2980", "trust-land")},
                            "2980", "trust-land") == "Nobody lived here at the 2020 census."
    assert _population_note({("2980", "trust-land"): 1529}, {("2980", "trust-land")},
                            "2980", "trust-land") == "1,529 people at the 2020 census."
    assert _districts_note([]).startswith("None.")
    assert _districts_note(["B District", "A District"]) == "A District, B District"

    # Every declared reason names a host and a date, so a later pass can tell a
    # measured block from a remembered one.
    for code, row in ROSTER_BLOCKED.items():
        assert row["host"] and len(row["measured"]) == 10 and row["why"], code
    for code, row in ROSTER_NOT_READ.items():
        assert row["host"] and len(row["measured"]) == 10, code
        assert row["page"].startswith("https://"), code
        assert row["page"] not in (other["page"] for c, other in
                                   ROSTER_NOT_READ.items() if c != code), code
    assert not (set(ROSTER_BLOCKED) & set(ROSTER_NOT_READ))
    # The not-read sentence names the page and the date, so a reader is sent
    # somewhere rather than told an absence with no remedy.
    one = _not_read_why({"host": "example.invalid", "measured": "2026-10-01",
                         "page": "https://example.invalid/council"})
    assert "https://example.invalid/council" in one and "2026-10-01" in one

    # The card lists the head of government first whatever order a page used,
    # and keeps the page's order within each group.
    assert [_office_rank(r) for r in ("Chairwoman", "Tribal Chairperson", "Chief",
                                      "President", "Vice-Chairman", "Sub-Chief",
                                      "Secretary/Treasurer", "Sergeant-at-Arms",
                                      "Council Member", "Director")] == [0, 0, 0, 0, 1, 1, 3, 4, 5, 5]
    members = [{"name": "A B", "role": "Treasurer"}, {"name": "C D", "role": "Council Member"},
               {"name": "E F", "role": "Chairman"}, {"name": "G H", "role": "Council Member"}]
    rec = {"source": "nation", "page": "https://example.invalid/council", "read": "2026-10-06",
           "members": members}
    got = roster_props("0001", {"0001": rec})
    assert [m["name"] for m in got["roster"]] == ["E F", "A B", "C D", "G H"], got
    assert got["rosterWhy"] is None and got["rosterNote"].endswith("read 2026-10-06.")
    carried = roster_props("0001", {"0001": dict(rec, carriedFrom="2026-09-29")})
    assert "last read 2026-09-29" in carried["rosterNote"] and carried["rosterRead"] == "2026-09-29"
    state = roster_props("0001", {"0001": dict(rec, source="state-list", listUpdated="2026-07-08",
                                               publisher="Wisconsin Department of Administration")})
    assert "updated 2026-07-08" in state["rosterNote"] and "no council of its own" in state["rosterNote"]
    assert roster_props("0002", {"0001": rec}) is None

    print("build-tribal-areas --selftest: OK — the join check fails three ways, "
          "the seat never invents a city, all %d blocked roster(s) name a host "
          "and a date, and all %d not-yet-read roster(s) name a distinct page"
          % (len(ROSTER_BLOCKED), len(ROSTER_NOT_READ)))
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--state")
    ap.add_argument("--tag")
    ap.add_argument("--out")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--rosters", action="store_true",
                    help="offline: re-stamp the shipped files from data/tribal-councils.json")
    args = ap.parse_args()
    if args.rosters:
        stamp_rosters()
        return 0
    if args.selftest:
        return 0 if selftest() else 1
    if args.check:
        return 0 if check() else 1
    if not args.state or not args.tag:
        ap.error("--state and --tag are both needed to build")
    build(args.state, args.tag, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
