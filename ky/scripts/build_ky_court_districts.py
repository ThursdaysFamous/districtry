#!/usr/bin/env python3
"""
Kentucky Court District Builder (the four courts, from statute text alone)
=========================================================================
Writes three boundary files that answer four courts:

    data/app/ky-supreme-court-districts.json    7 districts  (KRS 21A.010)
    data/app/ky-circuit-court-districts.json   57 circuits   (KRS 23A.020)
    data/app/ky-district-court-districts.json  59 districts  (KRS 24A.030)

THE COURT OF APPEALS DRAWS THE SUPREME COURT'S FILE, and that is the statute's
own instruction rather than a convenience: KRS 22A.010(2) says its districts
"shall correspond in geographical dimensions to the districts of the Supreme
Court, as defined in KRS Chapter 21A", with two judges from each. So three
geometries serve four layers, and nothing is drawn twice.

NO PUBLISHER IS ASKED AND NO MAP IS READ. Every one of these units is a group
of WHOLE COUNTIES named in the statute, and this instance already ships the
county fabric, so the build is a parse and a dissolve — offline, with the
statute text retained in `data/source/statutes/` (see its README for the one
recorded limitation: the exact PDF url each extraction came from was not
written down at fetch time). The Court of Justice publishes its own district
maps; they are a WITNESS to check a dissolve against, never the source.

WHY THE PARTITION IS THE GATE. A county list that is complete and disjoint is
the whole correctness question here: if a county appeared twice the dissolve
would hand one piece of ground to two courts, and if one were missing a reader
there would be told no court answers. All three statutes partition Kentucky's
120 counties EXACTLY ONCE, which is measured on every run rather than assumed,
and a failure names the county.

TWO PARSING TRAPS, BOTH OF WHICH FAILED SILENTLY WITH A PLAUSIBLE ANSWER when
this was first written, which is why each is a guard rather than a comment:

  * THE HISTORY BLOCK IS CUT BY LINE, never on the first occurrence of
    "Effective". 24A.030's own TITLE line carries "(Effective until January 1,
    2031)", so splitting on the word threw the whole statute away and reported
    ZERO units instead of raising.
  * A ROUND TEN IS ONE WORD BY TWO DIFFERENT RULES. Twentieth and Thirtieth
    keep their tens stem; Fortieth and Fiftieth drop a letter. Every paragraph's
    ordinal word is checked against its own paragraph number, so a statute that
    renumbers cannot parse quietly into the wrong unit.

DO NOT SIMPLIFY AFTER DISSOLVING. The app cancels an interior border only where
two features share coordinates EXACTLY, and `state-counties.json` is already
simplified, so a dissolve of it introduces no vertex and no seam. Simplifying
the result again would move the shared edges apart and draw hairlines between
neighbouring courts.

A SECOND VERSION OF 24A.030 IS ALREADY ENACTED, effective 2031-01-01 (2022 Ky.
Acts ch. 129 sec. 7), taking the district courts from 59 units to 58. It is
retained beside today's text and parsed by `--check` for ONE purpose: to prove
the three changes `WATCH.md` records are the statute's own and not a reading of
a note. It is never built. A dated redistricting with a known trigger rather
than a cycle, so WATCH.md carries its row.

Usage:
    python3 build_ky_court_districts.py          # writes the three files (needs shapely)
    python3 build_ky_court_districts.py --check  # offline, stdlib only, verifies the shipped files
"""

import argparse
import collections
import json
import math
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_INSTANCE = os.path.dirname(_HERE)
STATUTES = os.path.join(_INSTANCE, "data", "source", "statutes")
APP = os.path.join(_INSTANCE, "data", "app")
COUNTIES = os.path.join(APP, "state-counties.json")

# (statute file, the words that follow the ordinal, output file, unit count,
#  what one unit is called, the court the file answers)
TILINGS = (
    ("krs21A.010.txt", "District", "ky-supreme-court-districts.json", 7,
     "Supreme Court district", "KRS 21A.010"),
    ("krs23A.020.txt", "Judicial Circuit", "ky-circuit-court-districts.json", 57,
     "judicial circuit", "KRS 23A.020"),
    ("krs24A.030-until2031.txt", "Judicial District",
     "ky-district-court-districts.json", 59, "judicial district",
     "KRS 24A.030"),
)

ORD = ("First Second Third Fourth Fifth Sixth Seventh Eighth Ninth Tenth "
       "Eleventh Twelfth Thirteenth Fourteenth Fifteenth Sixteenth Seventeenth "
       "Eighteenth Nineteenth Twentieth").split()
TENS = {"Twenty": 20, "Thirty": 30, "Forty": 40, "Fifty": 50}
# A round ten is one word, and NOT by one rule: Twentieth and Thirtieth keep the
# tens stem while Fortieth and Fiftieth drop a letter. Spelled out rather than
# derived, because deriving it is what got it wrong.
ROUND = {"Twentieth": 20, "Thirtieth": 30, "Fortieth": 40, "Fiftieth": 50}

EARTH_KM = 6371.0088


def fail(msg):
    print("build-ky-court-districts: FAIL — " + msg)
    sys.exit(1)


def ordinal(word):
    """'Thirty-fourth' -> 34. Raises on anything it does not recognise."""
    if word in ORD:
        return ORD.index(word) + 1
    if word in ROUND:
        return ROUND[word]
    if "-" in word:
        head, tail = word.split("-", 1)
        if head in TENS and tail.capitalize() in ORD:
            return TENS[head] + ORD.index(tail.capitalize()) + 1
    raise ValueError("unrecognised ordinal word %r" % word)


def paragraphs(path):
    """One logical line per numbered paragraph, history block cut by LINE."""
    out, cur = [], ""
    with open(os.path.join(STATUTES, path)) as fh:
        for line in fh:
            line = line.strip()
            if re.match(r"^Effective\b", line) or line.startswith("History:"):
                break
            if re.match(r"^\(\d+\)", line):
                if cur:
                    out.append(cur)
                cur = line
            elif cur:
                cur += " " + line
    if cur:
        out.append(cur)
    if not out:
        fail("%s parsed to no numbered paragraph at all. The history block is "
             "cut by line; a title line carrying the word Effective must not "
             "take the statute with it." % path)
    return out


def parse(path, label):
    """[(unit number, [county basename, ...])] from one statute."""
    rows = []
    for para in paragraphs(path):
        m = re.match(r"^\((\d+)\)\s+(\S+)\s+" + re.escape(label)
                     + r"[.:]?\s*(.*)$", para)
        if not m:
            fail("%s: could not read a unit out of %r" % (path, para[:90]))
        number, word, rest = int(m.group(1)), m.group(2), m.group(3)
        try:
            spelled = ordinal(word)
        except ValueError as exc:
            fail("%s paragraph (%d): %s" % (path, number, exc))
        if spelled != number:
            fail("%s: paragraph (%d) is headed %r, which is unit %d. The "
                 "statute has been renumbered and this parse would put the "
                 "wrong counties in the wrong court."
                 % (path, number, word, spelled))
        rest = re.sub(r"\s+Count(y|ies)\s*\.?$", "", rest.strip()).rstrip(".")
        names = [p.strip() for p in re.split(r",| and ", rest) if p.strip()]
        if not names:
            fail("%s: unit %d names no county" % (path, number))
        rows.append((number, names))
    return rows


def county_geometry():
    """{basename: geometry} from the shipped county fabric."""
    with open(COUNTIES) as fh:
        feats = json.load(fh)["features"]
    out = {}
    for f in feats:
        name = (f.get("properties") or {}).get("BASENAME")
        if not name:
            fail("a county feature carries no BASENAME")
        if name in out:
            fail("%s appears twice in the county fabric" % name)
        out[name] = f["geometry"]
    return out


def check_partition(path, rows, counties):
    """Every county in exactly one unit, and no name the fabric lacks."""
    seen = collections.Counter(c for _n, cs in rows for c in cs)
    unknown = sorted(set(seen) - set(counties))
    if unknown:
        fail("%s names %d county/counties the fabric does not carry: %s"
             % (path, len(unknown), ", ".join(unknown)))
    twice = sorted(c for c, k in seen.items() if k > 1)
    if twice:
        fail("%s puts %s in more than one unit, so one piece of ground would "
             "be claimed by two courts" % (path, ", ".join(twice)))
    missing = sorted(set(counties) - set(seen))
    if missing:
        fail("%s leaves out %d county/counties, so a reader there would be "
             "told no court answers: %s" % (path, len(missing),
                                            ", ".join(missing)))


def rings_of(geometry):
    """Every linear ring of a Polygon or MultiPolygon, outer and inner alike."""
    kind = geometry.get("type")
    if kind == "Polygon":
        return list(geometry["coordinates"])
    if kind == "MultiPolygon":
        return [r for part in geometry["coordinates"] for r in part]
    fail("unexpected geometry type %r" % kind)


def ring_area_km2(ring):
    """Signed spherical area, so a hole subtracts and winding decides sign."""
    total = 0.0
    for i in range(len(ring) - 1):
        lon1, lat1 = math.radians(ring[i][0]), math.radians(ring[i][1])
        lon2, lat2 = math.radians(ring[i + 1][0]), math.radians(ring[i + 1][1])
        total += (lon2 - lon1) * (2 + math.sin(lat1) + math.sin(lat2))
    return total * EARTH_KM * EARTH_KM / 2.0


def measure(geometry):
    """Area the way a reader's ground is measured, holes subtracted."""
    return abs(sum(ring_area_km2(r) for r in rings_of(geometry)))


def build():
    try:
        from shapely.geometry import mapping, shape
        from shapely.ops import unary_union
    except ImportError:
        fail("the build path needs shapely (pip install -c "
             "scripts/requirements.txt shapely). `--check` is stdlib only.")
    counties = county_geometry()
    for path, label, out_name, want, unit_word, cite in TILINGS:
        rows = parse(path, label)
        if len(rows) != want:
            fail("%s parsed %d %ss, expected %d"
                 % (path, len(rows), unit_word, want))
        check_partition(path, rows, counties)
        features, worst = [], 0.0
        for number, names in rows:
            parts = [shape(counties[c]) for c in names]
            merged = unary_union(parts)
            # A dissolve of disjoint counties neither gains nor loses ground.
            want_area = sum(p.area for p in parts)
            worst = max(worst, abs(merged.area - want_area) / want_area)
            features.append({
                "type": "Feature",
                "properties": {"unit": number,
                               "counties": sorted(names),
                               "authority": cite},
                "geometry": mapping(merged),
            })
        if worst > 1e-9:
            fail("%s: a dissolve moved ground by %.2e of its own area"
                 % (path, worst))
        body = json.dumps({"type": "FeatureCollection", "features": features},
                          separators=(",", ":"))
        with open(os.path.join(APP, out_name), "w") as fh:
            fh.write(body)
        print("build-ky-court-districts: wrote %s — %d %ss, %.1f KB, "
              "area drift %.1e" % (out_name, len(rows), unit_word,
                                   len(body) / 1024.0, worst))


def check():
    counties = county_geometry()
    for path, label, out_name, want, unit_word, cite in TILINGS:
        rows = parse(path, label)
        if len(rows) != want:
            fail("%s parsed %d %ss, expected %d"
                 % (path, len(rows), unit_word, want))
        check_partition(path, rows, counties)
        full = os.path.join(APP, out_name)
        if not os.path.exists(full):
            fail("%s is missing. Run this builder without --check." % out_name)
        with open(full) as fh:
            shipped = json.load(fh)["features"]
        by_unit = {}
        for f in shipped:
            props = f.get("properties") or {}
            unit = props.get("unit")
            if unit in by_unit:
                fail("%s ships unit %r twice" % (out_name, unit))
            by_unit[unit] = f
        if len(by_unit) != len(rows):
            fail("%s ships %d %ss and the statute names %d"
                 % (out_name, len(by_unit), unit_word, len(rows)))
        worst = 0.0
        for number, names in rows:
            f = by_unit.get(number)
            if f is None:
                fail("%s ships no %s %d" % (out_name, unit_word, number))
            props = f["properties"]
            if props.get("counties") != sorted(names):
                fail("%s %s %d ships counties %r and the statute names %r"
                     % (out_name, unit_word, number, props.get("counties"),
                        sorted(names)))
            if props.get("authority") != cite:
                fail("%s %s %d cites %r, expected %r"
                     % (out_name, unit_word, number, props.get("authority"),
                        cite))
            # THE IDENTITY, re-derived from the fabric rather than trusted: the
            # shipped shape must cover exactly the ground its own counties do.
            drawn = measure(f["geometry"])
            named = sum(measure(counties[c]) for c in names)
            worst = max(worst, abs(drawn - named) / named)
        if worst > 1e-6:
            fail("%s: a shipped shape differs from its own counties' ground by "
                 "%.2e of its area, so the file and the statute disagree"
                 % (out_name, worst))
        print("build-ky-court-districts: %s — %d %ss, every county in exactly "
              "one, area identity within %.1e"
              % (out_name, len(rows), unit_word, worst))
    check_2031()
    print("build-ky-court-districts: OK — 3 file(s) answering 4 courts, the "
          "Court of Appeals on the Supreme Court's own districts (KRS "
          "22A.010(2))")


def check_2031():
    """The enacted 2031 district-court text, parsed to hold WATCH.md's row."""
    today = dict((n, tuple(cs))
                 for n, cs in parse("krs24A.030-until2031.txt",
                                    "Judicial District"))
    later = dict((n, tuple(cs))
                 for n, cs in parse("krs24A.030-from2031.txt",
                                    "Judicial District"))
    if len(later) != 58:
        fail("the 2031 district-court text parses to %d units, and WATCH.md "
             "records 58" % len(later))
    def where(table):
        return {c: n for n, cs in table.items() for c in cs}

    now, then = where(today), where(later)
    moves = {c: (now.get(c), then.get(c)) for c in set(now) | set(then)
             if now.get(c) != then.get(c)}
    expected = {"Edmonson": (38, 8), "Marshall": (58, 42),
                "Cumberland": (59, 58), "Monroe": (59, 58)}
    if moves != expected:
        fail("the 2031 text moves %r and WATCH.md records %r"
             % (moves, expected))
    print("build-ky-court-districts: the enacted 2031 text parses to 58 "
          "district(s) and moves exactly the four counties WATCH.md records")


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[1])
    ap.add_argument("--check", action="store_true",
                    help="verify the shipped files, write nothing")
    args = ap.parse_args()
    if args.check:
        check()
    else:
        build()


if __name__ == "__main__":
    main()
