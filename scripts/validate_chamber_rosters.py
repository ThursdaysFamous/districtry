#!/usr/bin/env python3
"""A legislative chamber's roster carries a record for every seat it elects.

WHY THIS EXISTS, MEASURED. A chamber roster built from a bulk export has no row
for a seat nobody holds, and until 2026-10-01 that absence reached readers three
ways at once. The card fell through to the factory's no-roster path and showed
only the district number with no explanation. Each legislature page's seat table
takes its own count from the roster's length, so it published a chamber smaller
than the one the state elects -- `ca/state-legislature.html` said "All 79 seats
on the California State Assembly" for a chamber of eighty, and
`ia/state-legislature.html` said "All 49 seats on the Iowa Senate" for a chamber
of fifty. And the roster's floor guard counted RECORDS, so a vacancy spent part
of the slack that exists to catch a truncated download.

None of the fleet's gates could see it. `validate_index.py` checks that a roster
has at least as many records as it expects, which a chamber one short satisfies;
`check_roster_retention.py` compares a change against its base, and a seat that
was never there is not a field that stopped being published. So this gate asks
the one question neither does: does the roster carry a key for every district
the chamber elects?

THE SEAT COUNT COMES FROM THE BUILDER THAT WRITES THE ROSTER, not from a table
here. Each chamber's own builder already states it (`CHAMBERS[...]["seats"]`)
because it needs it to write the records, and a second copy in a gate is how two
readers of one question come to disagree. The gate imports it.

WHAT A NAMELESS RECORD MAY SAY IS ALSO CHECKED, because the two kinds of empty
seat are different statements and only one of them is the chamber's:

  * `vacant: true` means the chamber's OWN members page says the seat is empty.
    It must carry `sourceUrl` -- the page that said it -- and `asOf`, the day it
    said it. A vacancy with no source is a claim about a seat with nothing behind
    it, which is exactly what the honesty rules forbid. It MAY carry
    `vacantWhy`, one plain sentence the card prints instead of the default, which
    exists because a chamber can say the seat is empty without using the word:
    Iowa's Senate roster ends a member's service with a past date and names
    nobody after them, where California's prints "Member Vacant". The default
    sentence would be false of Iowa's own cited page, so the record carries its
    own. An EMPTY `vacantWhy` is refused rather than silently falling back --
    a key present and blank is a sentence somebody meant to write.
  * no `name` and no `vacant` means our source named nobody. It must carry
    `asOf` and nothing is claimed about the seat.

A CHAMBER THAT ELECTS SEVERAL MEMBERS FROM EACH DISTRICT states it as
`per_district` beside `seats` (West Virginia's Senate: 17 districts, two
senators each, 2026-10-29). Its record for a district is `{"seats": N,
"members": [...]}`: `seats` must equal `per_district`, there may be no more
members than that, every member must carry a name, and a district listing
fewer members than it elects must carry `asOf`, because the card then says how
many the roster listed and on what day. A record that names one member under a
`name` key in such a chamber is refused, because the card for that chamber
reads `members` and would name nobody.

Usage:
    python3 scripts/validate_chamber_rosters.py            # the gate
    python3 scripts/validate_chamber_rosters.py --selftest  # proves both ways
"""

import importlib.util
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Each chamber-roster builder, and nothing else: a builder that writes one
# record per seat states its chamber's size, and that statement is what this
# gate reads. An instance whose chambers are built another way is not listed and
# is not checked, which the OK line says rather than implying coverage.
BUILDERS = (
    "ca/scripts/build_ca_legislature_roster.py",
    "ia/scripts/build_ia_legislature_roster.py",
    "tn/scripts/build_tn_legislature_roster.py",
    "ar/scripts/build_ar_legislature_roster.py",
    "ms/scripts/build_ms_legislature_roster.py",
    "la/scripts/build_la_legislature_roster.py",
    "mo/scripts/build_mo_legislature_roster.py",
    "ga/scripts/build_ga_legislature_roster.py",
    "va/scripts/build_va_legislature_roster.py",
    "wv/scripts/build_wv_legislature_roster.py",
    "pa/scripts/build_pa_legislature_roster.py",
    "nv/scripts/build_nv_legislature_roster.py",
    "az/scripts/build_az_legislature_roster.py",
    "nj/scripts/build_nj_legislature_roster.py",
    "nh/scripts/build_nh_legislature_roster.py",
    "tx/scripts/build_tx_legislature_roster.py",
    "fl/scripts/build_fl_legislature_roster.py",
)


def load_builder(rel):
    """Import a builder for its CHAMBERS table without running it."""
    path = os.path.join(REPO_ROOT, rel)
    if not os.path.exists(path):
        return None, "%s is gone; this gate reads its CHAMBERS table" % rel
    name = "chamber_builder_" + rel.replace("/", "_").replace(".py", "")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001
        return None, "%s could not be imported (%s: %s)" % (
            rel, exc.__class__.__name__, exc)
    chambers = getattr(module, "CHAMBERS", None)
    if not isinstance(chambers, dict) or not chambers:
        return None, "%s has no CHAMBERS table" % rel
    return chambers, None


def check_record(label, district, rec, per_district=1):
    """What a seat's record is allowed to say. Returns a list of problems."""
    if not isinstance(rec, dict):
        return ["%s district %s is not a record" % (label, district)]
    if per_district > 1:
        return check_multi_record(label, district, rec, per_district)
    if rec.get("name"):
        return []
    bad = []
    if rec.get("vacant"):
        if "vacantWhy" in rec and not str(rec.get("vacantWhy") or "").strip():
            bad.append("%s district %s carries an empty vacantWhy. The card "
                       "prints that sentence, so a blank one is a claim "
                       "somebody started and did not finish." % (label, district))
        if not rec.get("sourceUrl"):
            bad.append("%s district %s says the seat is vacant and names no "
                       "sourceUrl. A vacancy is the CHAMBER'S statement, so the "
                       "record carries the page that made it." % (label, district))
        if not rec.get("asOf"):
            bad.append("%s district %s says the seat is vacant and carries no "
                       "asOf, so a reader cannot tell how old the statement is."
                       % (label, district))
    elif not rec.get("asOf"):
        bad.append("%s district %s names nobody and carries no asOf. A record "
                   "that says nothing at all is the absence this gate exists to "
                   "stop." % (label, district))
    return bad


def check_multi_record(label, district, rec, per_district):
    """A district that elects several members: see the docstring."""
    bad = []
    members = rec.get("members")
    if not isinstance(members, list):
        return ["%s district %s carries no `members` list, and this chamber "
                "elects %d members per district, so its card would name nobody"
                % (label, district, per_district)]
    if rec.get("seats") != per_district:
        bad.append("%s district %s says it elects %r members, and the builder "
                   "says %d" % (label, district, rec.get("seats"), per_district))
    if len(members) > per_district:
        bad.append("%s district %s lists %d members for %d seats"
                   % (label, district, len(members), per_district))
    for m in members:
        if not isinstance(m, dict) or not m.get("name"):
            bad.append("%s district %s lists a member with no name" % (label, district))
    if len(members) < per_district and not rec.get("asOf"):
        bad.append("%s district %s lists %d of its %d members and carries no "
                   "asOf, so the card cannot say when the roster said so"
                   % (label, district, len(members), per_district))
    return bad


def check_named_chamber(tag, label, cfg):
    """A chamber whose districts are NAMED and elect different numbers of
    members, which New Hampshire's House is: 400 seats in 203 districts such
    as "Hillsborough 41", each electing one to ten. The builder states the
    plan as `districts` ({name: seats}) instead of a count, every record is
    {seats, members[, asOf]} whatever the seat count, and each is held to its
    own district's seats. Returns (problems, report line)."""
    districts = cfg["districts"]
    out = cfg.get("out")
    if not out or not districts or not all(
            isinstance(n, int) and n >= 1 for n in districts.values()):
        return (["%s states its districts without an `out` file or with a seat "
                 "count that is not a whole number of seats" % label], None)
    path = os.path.join(REPO_ROOT, tag, "data", "app", out)
    if not os.path.exists(path):
        return (["%s: %s is gone" % (label, out)], None)
    with open(path, encoding="utf-8") as fh:
        roster = json.load(fh)
    problems = []
    missing = [d for d in districts if d not in roster]
    if missing:
        problems.append("%s elects from %d named districts and its roster has no "
                        "record for %s" % (label, len(districts), ", ".join(missing)))
    extra = [d for d in roster if d not in districts]
    if extra:
        problems.append("%s's roster carries %s, which is not one of the districts "
                        "its builder states" % (label, ", ".join(sorted(extra))))
    named = unlisted = 0
    for district, seats in districts.items():
        rec = roster.get(district)
        if rec is None:
            continue
        problems.extend(check_multi_record(label, district, rec, seats))
        listed = len([m for m in (rec.get("members") or []) if isinstance(m, dict) and m.get("name")]) \
            if isinstance(rec, dict) else 0
        named += listed
        unlisted += max(0, seats - listed)
    total = sum(districts.values())
    return (problems, "  %-16s %3d seats — %3d named, 0 vacant, %d no member listed "
                      "(%d named districts electing 1 to %d each)"
                      % (label, total, named, unlisted, len(districts), max(districts.values())))


def run():
    problems = []
    lines = []
    for rel in BUILDERS:
        chambers, why = load_builder(rel)
        if why:
            problems.append(why)
            continue
        tag = rel.split("/")[0]
        for key, cfg in sorted(chambers.items()):
            label = "%s %s" % (tag, cfg.get("label") or key)
            if isinstance(cfg.get("districts"), dict):
                named_problems, line = check_named_chamber(tag, label, cfg)
                problems.extend(named_problems)
                if line:
                    lines.append(line)
                continue
            seats = cfg.get("seats")
            per = cfg.get("per_district") or 1
            out = cfg.get("out")
            if not seats or not out:
                problems.append(
                    "%s states no `seats` (or no `out`), so nothing can check "
                    "that its roster carries one record per seat. A chamber "
                    "whose size is not stated cannot have its count verified."
                    % label)
                continue
            path = os.path.join(REPO_ROOT, tag, "data", "app", out)
            if not os.path.exists(path):
                problems.append("%s: %s is gone" % (label, out))
                continue
            with open(path, encoding="utf-8") as fh:
                roster = json.load(fh)
            missing = [str(d) for d in range(1, seats + 1) if str(d) not in roster]
            if missing:
                problems.append(
                    "%s elects %d seats and its roster has no record for "
                    "district(s) %s. A seat with no record shows a reader the "
                    "district number and nothing else, and the page's own seat "
                    "table counts the chamber one short. Write a record: "
                    "`vacant: true` with a sourceUrl and asOf where the chamber "
                    "says the seat is empty, or asOf alone where our source "
                    "merely names nobody."
                    % (label, seats, ", ".join(missing)))
            named = vacant = unlisted = 0
            for d in range(1, seats + 1):
                rec = roster.get(str(d))
                if rec is None:
                    continue
                problems.extend(check_record(label, d, rec, per))
                if per > 1 and isinstance(rec, dict):
                    listed = len([m for m in rec.get("members") or [] if isinstance(m, dict) and m.get("name")])
                    named += listed
                    unlisted += max(0, per - listed)
                elif isinstance(rec, dict) and rec.get("name"):
                    named += 1
                elif isinstance(rec, dict) and rec.get("vacant"):
                    vacant += 1
                else:
                    unlisted += 1
            extra = [k for k in roster if not (k.isdigit() and 1 <= int(k) <= seats)]
            if extra:
                problems.append(
                    "%s elects districts 1-%d and its roster also carries %s. A "
                    "key that is not one of its seats cannot be rendered by the "
                    "chamber card." % (label, seats, ", ".join(sorted(extra))))
            lines.append("  %-16s %3d seats — %3d named, %d vacant, %d no member "
                         "listed%s" % (label, seats * per, named, vacant, unlisted,
                                       "" if per == 1 else " (%d districts, %d each)" % (seats, per)))
    return problems, lines


# Both directions, because a gate that has only ever seen a passing tree is a
# gate nobody has tested. Each case is a roster as it would ship.
CASES = (
    ({"1": {"name": "A"}, "2": {"vacant": True, "sourceUrl": "https://x/", "asOf": "2026-10-01"}},
     2, 0, "a named seat and a sourced, dated vacancy"),
    ({"1": {"name": "A"}, "2": {"asOf": "2026-10-01"}},
     2, 0, "a named seat and a dated record naming nobody"),
    ({"1": {"name": "A"}}, 2, 1, "a chamber of two with one seat absent"),
    ({"1": {"name": "A"}, "2": {"vacant": True, "asOf": "2026-10-01"}},
     2, 1, "a vacancy with no sourceUrl"),
    ({"1": {"name": "A"}, "2": {"vacant": True, "sourceUrl": "https://x/"}},
     2, 1, "a vacancy with no asOf"),
    ({"1": {"name": "A"}, "2": {}}, 2, 1, "a record that says nothing at all"),
    ({"1": {"name": "A"},
      "2": {"vacant": True, "sourceUrl": "https://x/", "asOf": "2026-10-01",
            "vacantWhy": "The roster names nobody after them."}},
     2, 0, "a vacancy carrying its own sentence"),
    ({"1": {"name": "A"},
      "2": {"vacant": True, "sourceUrl": "https://x/", "asOf": "2026-10-01",
            "vacantWhy": "   "}},
     2, 1, "a vacancy whose sentence is blank"),
)

# The same, for a chamber electing two members from each district.
MULTI_CASES = (
    ({"seats": 2, "members": [{"name": "A"}, {"name": "B"}]}, 0, "both members named"),
    ({"seats": 2, "members": [{"name": "A"}], "asOf": "2026-10-29"}, 0,
     "one member listed, dated"),
    ({"seats": 2, "members": [{"name": "A"}]}, 1, "one member listed, undated"),
    ({"seats": 2, "members": [{"name": "A"}, {"name": "B"}, {"name": "C"}]}, 1,
     "three members for two seats"),
    ({"seats": 1, "members": [{"name": "A"}, {"name": "B"}]}, 1,
     "a seat count that disagrees with the builder"),
    ({"seats": 2, "members": [{"name": "A"}, {}]}, 1, "a member with no name"),
    ({"name": "A"}, 1, "a single-member record in a two-member chamber"),
)


# The same, for a chamber of NAMED districts electing different numbers.
NAMED_CASES = (
    ({"A 1": {"seats": 1, "members": [{"name": "X"}]},
      "A 2": {"seats": 3, "members": [{"name": "Y"}], "asOf": "2026-11-11"}}, 0,
     "every named district carries a record, a short one dated"),
    ({"A 1": {"seats": 1, "members": [{"name": "X"}]}}, 1, "a named district absent"),
    ({"A 1": {"seats": 1, "members": [{"name": "X"}]},
      "A 2": {"seats": 3, "members": [{"name": "Y"}]}}, 1, "a short district undated"),
    ({"A 1": {"seats": 1, "members": [{"name": "X"}, {"name": "Z"}]},
      "A 2": {"seats": 3, "members": [{"name": "Y"}], "asOf": "2026-11-11"}}, 1,
     "two members for one seat"),
    ({"A 1": {"seats": 1, "members": [{"name": "X"}]},
      "A 2": {"seats": 2, "members": [{"name": "Y"}], "asOf": "2026-11-11"}}, 1,
     "a seat count that disagrees with the builder's plan"),
    ({"A 1": {"seats": 1, "members": [{"name": "X"}]},
      "A 2": {"seats": 3, "members": [{"name": "Y"}], "asOf": "2026-11-11"},
      "A 9": {"seats": 1, "members": []}}, 1, "a district the plan does not have"),
)


def selftest():
    bad = 0
    for roster, seats, want, why in CASES:
        found = [str(d) for d in range(1, seats + 1) if str(d) not in roster]
        problems = ["missing"] if found else []
        for d in range(1, seats + 1):
            rec = roster.get(str(d))
            if rec is not None:
                problems.extend(check_record("selftest", d, rec))
        got = 1 if problems else 0
        if got != want:
            bad += 1
            print("  SEAT  want=%d got=%d  (%s)" % (want, got, why))
    print("  SEAT  %d roster case(s), %d clean / %d refused"
          % (len(CASES), sum(1 for _, _, w, _ in CASES if not w),
             sum(1 for _, _, w, _ in CASES if w)))
    for rec, want, why in MULTI_CASES:
        got = 1 if check_record("selftest", 1, rec, 2) else 0
        if got != want:
            bad += 1
            print("  MULTI want=%d got=%d  (%s)" % (want, got, why))
    print("  MULTI %d two-member case(s), %d clean / %d refused"
          % (len(MULTI_CASES), sum(1 for _, w, _ in MULTI_CASES if not w),
             sum(1 for _, w, _ in MULTI_CASES if w)))
    import tempfile
    plan = {"A 1": 1, "A 2": 3}
    for roster, want, why in NAMED_CASES:
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "zz", "data", "app"))
            with open(os.path.join(tmp, "zz", "data", "app", "r.json"), "w") as fh:
                json.dump(roster, fh)
            global REPO_ROOT
            saved, REPO_ROOT = REPO_ROOT, tmp
            try:
                problems, _ = check_named_chamber("zz", "selftest", {"districts": plan, "out": "r.json"})
            finally:
                REPO_ROOT = saved
        got = 1 if problems else 0
        if got != want:
            bad += 1
            print("  NAMED want=%d got=%d  (%s)" % (want, got, why))
    print("  NAMED %d named-district case(s), %d clean / %d refused"
          % (len(NAMED_CASES), sum(1 for _, w, _ in NAMED_CASES if not w),
             sum(1 for _, w, _ in NAMED_CASES if w)))
    if bad:
        print("validate-chamber-rosters: SELFTEST FAILED")
        return 1
    print("validate-chamber-rosters: selftest OK — %d roster case(s)"
          % (len(CASES) + len(MULTI_CASES) + len(NAMED_CASES)))
    return 0


def main():
    if "--selftest" in sys.argv[1:]:
        sys.exit(selftest())
    problems, lines = run()
    for line in lines:
        print(line)
    if problems:
        for p in problems:
            print("validate-chamber-rosters: FAIL — %s" % p)
        sys.exit(1)
    print("validate-chamber-rosters: OK — every seat of %d chamber(s) across %d "
          "builder(s) carries a record, and every record that names nobody says "
          "which kind of empty it is. Chambers built another way are not listed "
          "here and are not checked." % (len(lines), len(BUILDERS)))


if __name__ == "__main__":
    main()
