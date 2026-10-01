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


def _record(cls, feat, clip, entry, gov, district_names, counts, known):
    props = feat["properties"]
    code = str(props.get("AIANNH"))
    blocked = ROSTER_BLOCKED.get(code)
    return {
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
            "roster": None,
            "rosterWhy": blocked["why"] if blocked else None,
            "rosterHost": blocked["host"] if blocked else None,
            "rosterMeasured": blocked["measured"] if blocked else None,
        },
    }


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
                             here.get(code, []), counts, known))
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
    for f in feats:
        p = f["properties"]
        print("build-tribal-areas: %s — %s, seat %s, %s, %.4f km2, %s resident(s), "
              "%d district(s) drawn, roster %s"
              % (tag, p["nation"], p["seat"], p["landClass"], p["areaKm2"],
                 p["population"], len(p["districts"]),
                 "named" if p["roster"] else "not named"))
    print("build-tribal-areas: OK — %s wrote %d area(s) in %s (state code %s)"
          % (tag, len(feats), state_name, state_code))
    return doc


def check():
    """Offline: every shipped file against the join, the Bureau's list and itself."""
    join, bia = load_join(), load_bia()
    seen = areas = 0
    for tag in sorted(os.listdir(REPO)):
        path = os.path.join(REPO, tag, "data", "app", "tribal-areas.json")
        if not os.path.exists(path):
            continue
        seen += 1
        doc = json.load(open(path))
        if doc["state"] not in join["statesCovered"]:
            raise RuntimeError(
                "%s ships tribal areas for %s and the join does not list it as "
                "covered — re-run the join rather than the layer"
                % (tag, doc["state"]))
        for feat in doc["features"]:
            areas += 1
            p = feat["properties"]
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
            # The one thing a card may never render is an unexplained absence.
            if p["roster"] is None and not p["rosterWhy"]:
                raise RuntimeError(
                    "%s: AIANNH %s names nobody and says why nowhere — add a "
                    "ROSTER_BLOCKED entry with the host and the date, or carry a "
                    "roster" % (tag, p["aiannh"]))
            if p["roster"] is None and p["aiannh"] not in ROSTER_BLOCKED:
                raise RuntimeError(
                    "%s: AIANNH %s ships a reason this module does not declare, "
                    "so nothing re-reads it" % (tag, p["aiannh"]))
    if not seen:
        raise RuntimeError("no instance ships tribal-areas.json, so this gate "
                           "would pass vacuously")
    orphans = sorted(set(ROSTER_BLOCKED) - {
        f["properties"]["aiannh"]
        for tag in os.listdir(REPO)
        for f in (json.load(open(os.path.join(REPO, tag, "data", "app",
                                              "tribal-areas.json")))["features"]
                  if os.path.exists(os.path.join(REPO, tag, "data", "app",
                                                 "tribal-areas.json")) else [])})
    if orphans:
        raise RuntimeError(
            "ROSTER_BLOCKED names AIANNH %s and no instance ships it — a "
            "measurement nothing reads is the shape this project keeps finding "
            "wrong" % ", ".join(orphans))
    print("build-tribal-areas --check: OK — %d instance(s), %d area(s); every "
          "government named by the join and listed by the Bureau, every seat and "
          "link theirs, and every unnamed roster explained"
          % (seen, areas))
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

    print("build-tribal-areas --selftest: OK — the join check fails three ways, "
          "the seat never invents a city, and all %d blocked roster(s) name a "
          "host and a date" % len(ROSTER_BLOCKED))
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--state")
    ap.add_argument("--tag")
    ap.add_argument("--out")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
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
