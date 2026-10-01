#!/usr/bin/env python3
"""
Build Kentucky's judge roster — `data/app/ky-judge-roster.json`
==============================================================

Turns `ky_judge_scraper.py`'s intermediate file into the roster the four court
cards read, keyed by tier and unit number:

    {"supreme": {"6": {"members": [...]}}, "appeals": {...},
     "circuit": {...}, "district": {...}}

THE KEY IS THE UNIT THE JUDGE WAS ELECTED FROM, which is the whole point of the
ask behind this pipeline: the Court of Justice prints that number beside each
judge, so nothing here is inferred from a county of residence. A judge's
numbered DIVISION rides along as a label on the person and is never a key — a
division is a seat elected by the whole circuit (KRS 23A.040 and after) with no
geometry at all, so keying on one would invent districts that do not exist.

FOUR TIERS, THREE GEOMETRIES, AND FAMILY COURT. The app draws three boundary
files for four layers, because KRS 22A.010(2) puts the Court of Appeals on the
Supreme Court's districts. Family Court is a division of Circuit Court under
Ky. Const. 112(6) and its judges are elected from the circuit, so they join the
`circuit` tier carrying their own court name rather than becoming a fifth tiling
nothing draws.

EVERY UNIT IS CHECKED AGAINST THE SHIPPED TILINGS, in both directions, because
this file's only job is to be joinable: a unit the roster names that no boundary
file carries would put a judge nowhere, and the per-tier counts below are what
catch a source whose numbering has moved. Jefferson's circuit 30 and district 30
are the one expected absence — its county page ships no judge rows, measured and
recorded in the scraper — and they are named in the output as asked-about rather
than left to read as an oversight, so the card can say which it is.

A VACANCY IS THE COURT'S OWN WORD. A card whose name is `Vacant` is the Court of
Justice saying nobody holds that seat, which is what licenses a vacancy claim;
it ships as `vacant: true` with the page and read date, never as a person.

Usage:
    python3 ky/scripts/build_ky_judges.py             # build
    python3 ky/scripts/build_ky_judges.py --check     # offline drift gate
    python3 ky/scripts/build_ky_judges.py --selftest  # offline, no files needed
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
REPO = os.path.dirname(INSTANCE)

SCRAPE = os.path.join(INSTANCE, "data", "source", "ky-judges-scrape.json")
OUT = os.path.join(INSTANCE, "data", "app", "ky-judge-roster.json")

GEOMETRY = {
    "supreme": os.path.join(INSTANCE, "data", "app", "ky-supreme-court-districts.json"),
    "appeals": os.path.join(INSTANCE, "data", "app", "ky-supreme-court-districts.json"),
    "circuit": os.path.join(INSTANCE, "data", "app", "ky-circuit-court-districts.json"),
    "district": os.path.join(INSTANCE, "data", "app", "ky-district-court-districts.json"),
}

# THE UNIT COUNT IS AN IDENTITY, NOT A FLOOR, and it is derived rather than
# written down: every unit the shipped boundary files carry must appear in the
# roster except the ones ASKED_ABOUT records as unpublished. A floor would pass
# a run that quietly lost a circuit; this names the circuit. It also keeps
# itself true across a redistricting — KRS 24A.030's already-enacted 2031 text
# takes the district courts from 59 to 58 — because it reads the files rather
# than a number typed here.
#
# The JUDGE count is a floor, because how many judges a circuit or district
# elects is set elsewhere in KRS 23A and 24A and is not measured here. The two
# appellate tiers are the exception and are exact, the constitution fixing them:
# one justice per Supreme Court district, two judges per Court of Appeals
# district (KRS 22A.010(1)).
#
# MEASURED 2026-10-01, which is where these floors come from: supreme 7 units /
# 7 judges, appeals 7 / 14, circuit 56 / 135 (84 circuit-court judges and 51
# family-court judges, Family Court being a division of Circuit Court elected
# from the circuit), district 58 / 99. The floors sit about a tenth below the
# measured figures, low enough not to fire on an ordinary vacancy and high
# enough that a parse losing a page's worth of judges fails.
EXPECT = {
    "supreme": {"members": 7, "exact": True},
    "appeals": {"members": 14, "exact": True},
    "circuit": {"members": 120, "exact": False},
    "district": {"members": 88, "exact": False},
}

# The units whose judges this source does not name, each with the reason. These
# are carried INTO the output so a card can say "asked about" rather than go
# quiet, and audited on every run: an entry that stops being absent FAILS, which
# is how a fixed source gets noticed instead of a stale note surviving it.
ASKED_ABOUT = {
    ("circuit", 30): "jefferson-page-empty",
    ("district", 30): "jefferson-page-empty",
}
ASKED_ABOUT_NOTE = (
    "Not named here. The Kentucky Court of Justice lists the judges for every "
    "other circuit and district in the state, and lists none for this one \u2014 "
    "Jefferson County's own page on its site leaves them out. We asked the court "
    "system about it on 1 October 2026 and are waiting for an answer. Until one "
    "comes, this card names nobody rather than guessing."
)


def fail(msg):
    sys.stderr.write("build-ky-judges: FAIL — %s\n" % msg)
    raise SystemExit(1)


def units_of(path):
    with open(path) as fh:
        data = json.load(fh)
    out = set()
    for feature in data.get("features", []):
        unit = (feature.get("properties") or {}).get("unit")
        if unit is not None:
            out.add(int(unit))
    return out


def member(row):
    """One roster record. A vacancy is the court's word, not a person's name."""
    vacant = row["name"].strip().lower() == "vacant"
    rec = {}
    if vacant:
        rec["vacant"] = True
    else:
        rec["name"] = row["name"]
    if row.get("role"):
        rec["role"] = row["role"]
    if row.get("court"):
        rec["court"] = row["court"]
    if row.get("division") is not None:
        rec["division"] = row["division"]
    if row.get("profileUrl") and not vacant:
        rec["profileUrl"] = row["profileUrl"]
    return rec


def sort_key(rec):
    # Division order where there is one, then court name, then the person — a
    # bench reads in the order its seats are numbered.
    return (rec.get("division") if rec.get("division") is not None else 0,
            rec.get("court") or "",
            rec.get("name") or "")


def assemble(scrape, geometry_units):
    tiers = {t: {} for t in EXPECT}
    seen = set()
    for row in scrape["rows"]:
        tier = row["tier"]
        if tier not in tiers:
            fail("unknown tier %r in the scrape" % tier)
        # The same judge is printed on every county page in their circuit, so
        # the de-duplication key is the seat, not the page.
        key = (tier, row["unit"], row.get("division"), row.get("court"), row["name"])
        if key in seen:
            continue
        seen.add(key)
        tiers[tier].setdefault(row["unit"], []).append(member(row))

    for tier, units in tiers.items():
        known = geometry_units[tier]
        stray = sorted(set(units) - known)
        if stray:
            fail("%s tier names unit(s) %s that no shipped boundary file carries, "
                 "so those judges would join nothing. Either the source's "
                 "numbering has moved or a statute has: re-read both before "
                 "shipping." % (tier, ", ".join(str(s) for s in stray)))

        # Every unit except the recorded absences, named when one goes missing.
        absent = {u for (tr, u) in ASKED_ABOUT if tr == tier}
        missing = sorted(known - absent - set(units))
        if missing:
            fail("%s tier names no judge for unit(s) %s. Every unit the boundary "
                 "file carries must either have a judge or be recorded in "
                 "ASKED_ABOUT with the measurement behind it, so this is a source "
                 "that has changed or a parse that has slipped — not something to "
                 "ship a roster short of."
                 % (tier, ", ".join(str(m) for m in missing)))

        want = EXPECT[tier]
        members = sum(len(v) for v in units.values())
        if want["exact"]:
            if members != want["members"]:
                fail("%s tier has %d judges; the constitution fixes this tier at "
                     "%d, so a difference is either a source change or a parse "
                     "that has slipped" % (tier, members, want["members"]))
        elif members < want["members"]:
            fail("%s tier has %d judges, below the floor of %d — too few to ship "
                 "without a person looking" % (tier, members, want["members"]))

        for unit in units:
            units[unit].sort(key=sort_key)

    # The expected absences, audited in both directions.
    for (tier, unit), reason in sorted(ASKED_ABOUT.items()):
        if unit not in geometry_units[tier]:
            fail("ASKED_ABOUT names %s unit %d, which no boundary file carries — "
                 "the entry has outlived its unit" % (tier, unit))
        if unit in tiers[tier]:
            fail("ASKED_ABOUT says %s unit %d names nobody, and the scrape found "
                 "%d judge(s) for it. That is the source being FIXED: delete the "
                 "entry, re-read the note beside it, and re-run."
                 % (tier, unit, len(tiers[tier][unit])))

    payload = {
        "source": scrape["source"],
        "readOn": scrape["readOn"],
        "askedAbout": {
            "%s-%d" % (tier, unit): {"reason": reason, "note": ASKED_ABOUT_NOTE}
            for (tier, unit), reason in ASKED_ABOUT.items()
        },
        "tiers": {
            tier: {str(unit): {"members": members}
                   for unit, members in sorted(units.items())}
            for tier, units in tiers.items()
        },
    }
    return payload


def build(check=False):
    if not os.path.exists(SCRAPE):
        fail("%s is missing — run ky/scripts/ky_judge_scraper.py first"
             % os.path.relpath(SCRAPE, REPO))
    with open(SCRAPE) as fh:
        scrape = json.load(fh)
    geometry_units = {t: units_of(p) for t, p in GEOMETRY.items()}
    payload = assemble(scrape, geometry_units)
    text = json.dumps(payload, indent=1, sort_keys=True) + "\n"

    if check:
        if not os.path.exists(OUT):
            fail("%s is missing" % os.path.relpath(OUT, REPO))
        with open(OUT) as fh:
            if fh.read() != text:
                fail("%s does not match what this builder writes from the "
                     "retained scrape — rebuild it" % os.path.relpath(OUT, REPO))
        counts = {t: (len(v), sum(len(u["members"]) for u in v.values()))
                  for t, v in payload["tiers"].items()}
        print("build-ky-judges: OK — " + ", ".join(
            "%s %d units/%d judges" % (t, c[0], c[1]) for t, c in sorted(counts.items()))
            + "; %d unit(s) recorded as asked about" % len(payload["askedAbout"]))
        return

    with open(OUT, "w") as fh:
        fh.write(text)
    counts = {t: (len(v), sum(len(u["members"]) for u in v.values()))
              for t, v in payload["tiers"].items()}
    print("build-ky-judges: wrote %s — " % os.path.relpath(OUT, REPO) + ", ".join(
        "%s %d units/%d judges" % (t, c[0], c[1]) for t, c in sorted(counts.items())))


def selftest():
    geometry_units = {"supreme": set(range(1, 8)), "appeals": set(range(1, 8)),
                      "circuit": set(range(1, 58)), "district": set(range(1, 60))}
    rows = []
    for unit in range(1, 8):
        rows.append({"name": "Justice %d" % unit, "role": "Justice",
                     "court": "Supreme Court", "tier": "supreme", "unit": unit,
                     "division": None, "profileUrl": None})
        for div in (1, 2):
            rows.append({"name": "Appeals %d-%d" % (unit, div), "role": "Judge",
                         "court": "Court of Appeals", "tier": "appeals",
                         "unit": unit, "division": div, "profileUrl": None})
    for unit in range(1, 58):
        if unit == 30:
            continue  # Jefferson, the recorded absence
        for div in (1, 2, 3):
            rows.append({"name": "Circuit %d-%d" % (unit, div), "role": "Judge",
                         "court": "Circuit Court", "tier": "circuit", "unit": unit,
                         "division": div, "profileUrl": None})
    for unit in range(1, 60):
        if unit == 30:
            continue
        for div in (1, 2, 3):
            rows.append({"name": "District %d-%d" % (unit, div), "role": "Judge",
                         "court": "District Court", "tier": "district", "unit": unit,
                         "division": div, "profileUrl": None})
    scrape = {"source": {"publisher": "selftest"}, "readOn": "2026-10-01", "rows": rows}

    payload = assemble(scrape, geometry_units)
    assert len(payload["tiers"]["supreme"]) == 7
    assert sum(len(u["members"]) for u in payload["tiers"]["appeals"].values()) == 14
    assert "30" not in payload["tiers"]["circuit"]
    assert set(payload["askedAbout"]) == {"circuit-30", "district-30"}

    # The same judge printed on several county pages is one seat.
    dup = dict(scrape, rows=rows + [dict(rows[-1])])
    assert assemble(dup, geometry_units)["tiers"] == payload["tiers"], \
        "a judge repeated across county pages must de-duplicate to one record"

    # A vacancy is never a person called Vacant.
    vac = [dict(r) for r in rows]
    vac[0] = dict(vac[0], name="Vacant")
    got = assemble(dict(scrape, rows=vac), geometry_units)["tiers"]["supreme"]
    seat = [m for unit in got.values() for m in unit["members"] if m.get("vacant")]
    assert len(seat) == 1 and "name" not in seat[0], seat

    # A unit the boundary file carries and the roster does not is NAMED, which a
    # floor could never do.
    short = [r for r in rows if not (r["tier"] == "circuit" and r["unit"] == 7)]
    try:
        assemble(dict(scrape, rows=short), geometry_units)
    except SystemExit:
        pass
    else:
        raise AssertionError("a unit with no judge and no ASKED_ABOUT entry must fail")

    # A unit no boundary file carries is refused rather than shipped unjoinable.
    stray = rows + [{"name": "Nowhere", "role": "Judge", "court": "Circuit Court",
                     "tier": "circuit", "unit": 99, "division": None, "profileUrl": None}]
    try:
        assemble(dict(scrape, rows=stray), geometry_units)
    except SystemExit:
        pass
    else:
        raise AssertionError("a unit outside the shipped tilings must fail the build")

    # And a fixed source turns the build red rather than passing quietly.
    fixed = rows + [{"name": "Louisville Judge", "role": "Judge",
                     "court": "Circuit Court", "tier": "circuit", "unit": 30,
                     "division": 1, "profileUrl": None}]
    try:
        assemble(dict(scrape, rows=fixed), geometry_units)
    except SystemExit:
        pass
    else:
        raise AssertionError("a recorded absence that starts publishing must fail")

    print("build-ky-judges: selftest OK — tier counts, de-duplication, vacancy "
          "shape, unjoinable unit refused, and a fixed source failing loudly")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="offline drift gate")
    ap.add_argument("--selftest", action="store_true", help="offline, needs no files")
    args = ap.parse_args()
    if args.selftest:
        selftest()
        return
    build(check=args.check)


if __name__ == "__main__":
    main()
