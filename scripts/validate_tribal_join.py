#!/usr/bin/env python3
"""Hold the land-to-government table to the two things that can make it wrong.

`data/tribal-government-join.json` says which government holds each piece of
tribal land the fleet answers over. No publisher provides that join: the Census
draws the land and names no government, the Bureau of Indian Affairs names the
governments and draws no land, and matching them by name leaves 40 of 312
reservations and 10 of 177 trust lands unmatched. So the table is written by hand,
and a hand-written table needs checking in both directions:

  - **A piece of land with no entry.** If the Census publishes tribal land inside
    a state the table claims to cover and the table has no entry for it, the app
    would draw a shape and name nobody. That fails.
  - **An entry naming a government that does not exist.** If an entry names a
    government the Bureau's own list does not carry, the app would print a name
    no federal publisher recognises. That fails too.

The first direction needs the Census, so it runs on `--measure`. The second is
offline and runs in CI, together with every check that can be made without the
network: that each entry's government and its parent are named exactly as the
Bureau names them, that the seat state agrees with the Bureau's own, and that
every piece of land recorded would still be kept by the ruled cross-state floor.

WHY THE KEY IS THE CENSUS'S AIANNH CODE
---------------------------------------
Measured 2026-09-30: a reservation and its own off-reservation trust land carry
the SAME AIANNH code (Bois Forte's reservation and trust land are both 0335), so
one code is one government's land holdings and the table has one entry per
government rather than one per shape. Names cannot be the key -- the Census calls
them "Bois Forte Reservation" and "Bois Forte Off-Reservation Trust Land" while
the Bureau calls the government "Minnesota Chippewa Tribe - Bois Forte Band (Nett
Lake)".

WHY A STATE CAN BE COVERED WITHOUT AN INSTANCE, AND AN INSTANCE WITHOUT COVERAGE
-------------------------------------------------------------------------------
The table grows state by state with the build sequence, so every state the fleet
answers for must be named in exactly one of `statesCovered` and
`statesNotYetCovered` -- naming none is how a state quietly ships with no join at
all. Minnesota is covered and has no live instance, which is allowed and is
printed: its records were measured while the instance was still dark.

Usage:
    python3 scripts/validate_tribal_join.py --check      # offline, in CI
    python3 scripts/validate_tribal_join.py --measure    # live, against the Census
    python3 scripts/validate_tribal_join.py --selftest   # offline, tests the gate
"""

import argparse
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JOIN = os.path.join(REPO_ROOT, "data", "tribal-government-join.json")
METROS = os.path.join(REPO_ROOT, "metros.json")

# Which state each instance answers over. ny and ca answer for one city each, so
# their landing name is not a state and cannot be read as one. Every tag in
# metros.json must appear here or the gate fails, which is what stops a new
# instance shipping with no tribal join decision taken either way.
STATE_OF_INSTANCE = {
    "il": "Illinois",
    "ny": "New York",
    "ca": "California",
    "wi": "Wisconsin",
    "ia": "Iowa",
    "mi": "Michigan",
    "mn": "Minnesota",
    "ky": "Kentucky",
    "in": "Indiana",
    "nc": "North Carolina",
}


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _governments():
    import bia_tribal_governments as bia
    return {g["name"]: g for g in bia.load()["governments"]}


def _problems(doc, govs, instance_states):
    """Every offline problem with this table, as reader-ready sentences."""
    out = []
    covered = doc.get("statesCovered") or []
    pending = doc.get("statesNotYetCovered") or []
    areas = doc.get("areas") or {}

    if not covered:
        out.append("statesCovered is empty, so this table covers nothing and gates nothing")
    for label, lst in (("statesCovered", covered), ("statesNotYetCovered", pending)):
        if lst != sorted(lst):
            out.append("%s is not sorted" % label)
        if len(set(lst)) != len(lst):
            out.append("%s names a state twice" % label)
    both = sorted(set(covered) & set(pending))
    if both:
        out.append("named as both covered and not yet covered: %s" % ", ".join(both))

    named = set(covered) | set(pending)
    for state in sorted(instance_states):
        if state not in named:
            out.append(
                "%s has a live app and is named in neither list, so nothing decides "
                "whether its tribal land needs an entry" % state
            )

    if list(areas) != sorted(areas):
        out.append("areas are not sorted by code")

    # The floor this table was built under, read from the reader rather than
    # restated, so the two cannot come to disagree about what counts.
    import tribal_areas as ta

    for code, entry in areas.items():
        where = "area %s" % code
        if not (len(code) == 4 and code.isdigit()):
            out.append("%s: not a four-digit AIANNH code" % where)
        gov = entry.get("government")
        shared = entry.get("governments")
        if shared is not None:
            # An area several governments share (Oklahoma's statistical areas,
            # where the Census's own name for one area names several nations):
            # every one must be the Bureau's, each with its own recorded seat
            # state, and the entry must not also name one government alone.
            if gov is not None:
                out.append("%s: names one government and a shared list" % where)
            if len(shared) < 2 or len(set(shared)) != len(shared):
                out.append("%s: a shared list must name two or more distinct "
                           "governments" % where)
            states_rec = entry.get("governmentStates") or []
            if len(states_rec) != len(shared):
                out.append("%s: governmentStates does not give one seat state per "
                           "government" % where)
            for i, name in enumerate(shared):
                if name not in govs:
                    out.append("%s: names %r, which the Bureau's own list does not "
                               "carry" % (where, name))
                elif i < len(states_rec) and states_rec[i] != govs[name].get("state"):
                    out.append("%s: seat of %r recorded as %r, the Bureau says %r"
                               % (where, name, states_rec[i], govs[name].get("state")))
        elif not gov:
            out.append("%s: names no government" % where)
        elif gov not in govs:
            out.append(
                "%s: names %r, which the Bureau's own list does not carry" % (where, gov)
            )
        else:
            seat = entry.get("governmentState")
            theirs = govs[gov].get("state")
            if seat != theirs:
                out.append(
                    "%s: seat recorded as %r, the Bureau says %r" % (where, seat, theirs)
                )
        parent = entry.get("parentGovernment")
        if parent is not None and parent not in govs:
            out.append(
                "%s: parent %r is not in the Bureau's own list" % (where, parent)
            )
        if parent is not None and parent == gov:
            out.append("%s: is its own parent" % where)

        lands = entry.get("lands") or []
        if not lands:
            out.append("%s: has no land, so nothing would be drawn for it" % where)
        states = entry.get("states") or []
        for land in lands:
            st = land.get("state")
            if st not in states:
                out.append("%s: land in %r is not in the entry's own state list" % (where, st))
            if st not in covered:
                out.append(
                    "%s: land recorded in %r, which this table does not claim to cover"
                    % (where, st)
                )
            if land.get("class") not in ta.drawn_classes(st):
                out.append(
                    "%s: land class %r is not one a government holds" % (where, land.get("class"))
                )
            km2 = land.get("km2")
            share = land.get("share")
            if km2 is None or share is None:
                out.append("%s: land %r carries no measurement" % (where, land.get("name")))
                continue
            if not (km2 > 0 and (share >= ta.KEEP_SHARE or km2 >= ta.KEEP_AREA_KM2)):
                out.append(
                    "%s: land %r is recorded at %s km2 / %s of the area, which the floor "
                    "leaves out — it should not be in this table"
                    % (where, land.get("name"), km2, share)
                )
    return out


def check():
    sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))
    if not os.path.exists(JOIN):
        raise SystemExit("%s is missing" % os.path.relpath(JOIN, REPO_ROOT))
    doc = _load(JOIN)
    govs = _governments()

    metros = _load(METROS)["metros"]
    unknown = [m["tag"] for m in metros if m["tag"] not in STATE_OF_INSTANCE]
    if unknown:
        raise SystemExit(
            "metros.json carries instance(s) this gate has no state for: %s\n"
            "Add them to STATE_OF_INSTANCE in %s."
            % (", ".join(unknown), os.path.relpath(__file__, REPO_ROOT))
        )
    instance_states = {STATE_OF_INSTANCE[m["tag"]] for m in metros}

    problems = _problems(doc, govs, instance_states)
    if problems:
        print("FAIL data/tribal-government-join.json")
        for p in problems:
            print("  - %s" % p)
        return 1

    areas = doc["areas"]
    lands = sum(len(e["lands"]) for e in areas.values())
    covered = doc["statesCovered"]
    dark = sorted(set(covered) - instance_states)
    print("OK data/tribal-government-join.json: %d governments over %d pieces of land in %s"
          % (len(areas), lands, ", ".join(covered)))
    if dark:
        print("   covered with no live app yet: %s" % ", ".join(dark))
    pending = doc.get("statesNotYetCovered") or []
    if pending:
        print("   not yet covered: %s" % ", ".join(pending))
    return 0


def measure():
    """Live: the Census's own answer for every covered state must match the table."""
    sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))
    import tribal_areas as ta

    doc = _load(JOIN)
    areas = doc["areas"]
    resolved = ta.resolve_layers()
    ids = resolved[doc.get("vintage") or ta.DEFAULT_VINTAGE]
    for note in ta.check_vintage_counts(resolved):
        print("NOTE %s" % note)

    missing, extra = [], []
    seen = set()
    for state in doc["statesCovered"]:
        poly, geoid = ta.state_polygon(state)
        print("control OK: %s is state code %s" % (state, geoid))
        for cls in ta.drawn_classes(state):
            if cls not in ids:
                continue
            for feat in ta.fetch_layer(ta.AIANNHA, ids[cls], fields=ta.AREA_FIELDS):
                geom = feat.get("geometry")
                if not geom:
                    continue
                got = ta.clip_to_state(geom, poly["geometry"])
                if not got["keep"]:
                    continue
                props = feat.get("properties") or {}
                code = props.get("AIANNH")
                name = props.get("NAME")
                if code not in areas:
                    missing.append((state, cls, code, name, round(got["inside_km2"], 3)))
                    continue
                seen.add((code, cls, state))
    for code, entry in areas.items():
        for land in entry["lands"]:
            key = (code, land["class"], land["state"])
            if key not in seen:
                extra.append((code, entry.get("government") or " / ".join(entry["governments"]),
                              land["name"], land["state"]))

    for state, cls, code, name, km2 in missing:
        print("MISSING %s in %s: %s %r (%s km2) has no entry" % (cls, state, code, name, km2))
    for code, gov, name, state in extra:
        print("STALE %s (%s): %r in %s is in the table and the Census no longer keeps it there"
              % (code, gov, name, state))
    if missing or extra:
        print("FAIL %d piece(s) of land with no entry, %d entry land(s) nothing matched"
              % (len(missing), len(extra)))
        return 1
    print("OK every piece of tribal land the Census keeps in %s has an entry, and every "
          "entry's land is still there" % ", ".join(doc["statesCovered"]))
    return 0


def selftest():
    """Offline: the gate catches each thing it exists to catch."""
    sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))
    import copy

    doc = _load(JOIN)
    govs = _governments()
    states = {"Illinois"}
    assert not _problems(doc, govs, states), _problems(doc, govs, states)
    checks = 1

    def broken(mutate):
        bad = copy.deepcopy(doc)
        mutate(bad)
        return _problems(bad, govs, states)

    code = sorted(doc["areas"])[0]

    cases = [
        ("a government the Bureau does not carry",
         lambda d: d["areas"][code].update(government="Nation of Nowhere")),
        ("a seat that disagrees with the Bureau",
         lambda d: d["areas"][code].update(governmentState="ZZ")),
        ("a parent that does not exist",
         lambda d: d["areas"][code].update(parentGovernment="Nation of Nowhere")),
        ("an entry with no land",
         lambda d: d["areas"][code].update(lands=[])),
        ("land in a state the table does not claim to cover",
         lambda d: d["areas"][code]["lands"][0].update(state="Ohio")),
        ("land the ruled floor leaves out",
         lambda d: d["areas"][code]["lands"][0].update(km2=0.0001, share=0.0001)),
        ("a land class no government holds",
         lambda d: d["areas"][code]["lands"][0].update(**{"class": "otsa"})),
        ("a live state named in neither list",
         lambda d: d.update(statesCovered=["Minnesota"], statesNotYetCovered=[])),
        ("a state named as both covered and pending",
         lambda d: d.update(statesNotYetCovered=d["statesNotYetCovered"] + ["Illinois"])),
        ("an empty covered list",
         lambda d: d.update(statesCovered=[])),
        ("a shared area naming a government the Bureau does not carry",
         lambda d: d["areas"]["5720"]["governments"].__setitem__(0, "Nation of Nowhere")),
        ("a shared area whose seat states do not line up",
         lambda d: d["areas"]["5720"].update(governmentStates=["OK"])),
        ("a shared area that also names one government",
         lambda d: d["areas"]["5720"].update(government="Cherokee Nation")),
        ("a statistical area outside the one state allowed to draw it",
         lambda d: d["areas"]["5720"]["lands"][0].update(state="Illinois")),
    ]
    for label, mutate in cases:
        assert broken(mutate), "the gate must catch %s" % label
        checks += 1

    print("OK validate_tribal_join selftest: %d assertions" % checks)
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="offline gate, runs in CI")
    ap.add_argument("--measure", action="store_true", help="live check against the Census")
    ap.add_argument("--selftest", action="store_true", help="offline, tests the gate itself")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if args.measure:
        return measure()
    if args.check:
        return check()
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
