#!/usr/bin/env python3
"""
Build Arkansas's two court layers from whole counties, dissolved from the
shipped county fabric:

  ar/data/app/ar-appeals-districts.json   the Court of Appeals' 7 districts
  ar/data/app/ar-judicial-circuits.json   the 28 judicial circuits

    python3 ar/scripts/build_ar_court_districts.py          # writes (needs shapely)
    python3 ar/scripts/build_ar_court_districts.py --check  # offline, stdlib only

The dissolve, the partition gate and the offline check are
scripts/whole_county_courts.py, shared with the other states; this file says
where Arkansas's county lists come from and how they are read. Every source is
kept in ar/data/source/courts/ with its address, read date and SHA-256 (see
its README); no judge is named in any of them.

THE COURT OF APPEALS. Act 1812 of 2003 divides the state into seven districts
"for the election of judges to the Arkansas Court of Appeals" and names each
district's counties. The act is read as the state GIS office's metadata quotes
it, and the state's own Appeals Court Districts layer, overlaid on this
instance's counties, must put every county where the act does. How many judges
each district elects is read from the court's own district map page, which
lists two positions in five districts and one in two: twelve judges.

THE CIRCUITS. The Administrative Office of the Courts' circuit judge directory
lists every judge under every county the judge serves, with the judge's
circuit and division. That is the source, and it is checked three ways:
every county must sit in exactly one circuit; every judge of a circuit must
serve every one of its counties, since a judge serving only some of them would
mean the circuit is not one electorate of whole counties; and the state's
Circuit Court Districts layer, its court-ordered subdistricts counted as their
circuit, must put every county in the same circuit. The number of divisions
is the circuit's judge count, and the statewide total is pinned (126), so a
directory that gains or loses a judge stops the build until someone reads why.
It will gain one on January 1, 2027, when the judgeship Act 220 of 2025 added
in the 19th West takes office (WATCH.md carries the date).

THE SUBDISTRICTS ARE NOT DRAWN. A federal court order (Hunt v. State of
Arkansas, No. PB-C-89-405, E.D. Ark., 1991, amended 1992 and 2002) created two
election subdistricts in each of five circuits; judges elected from them hear
cases across the whole circuit. Which judgeships each subdistrict elects is set
by the court and was not read, so the circuit is drawn whole and its card says
the subdistricts exist. The five circuits are read from the order's own words
as the circuit layer's metadata quotes them.

WHO IS NOT HERE. The state district courts (41 districts, some smaller than a
county) are a different court and not drawn. The Supreme Court is elected
statewide. Nobody is named: gaps ar-appeals-judges and ar-circuit-judges.
"""

import argparse
import collections
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)), "scripts"))

import whole_county_courts as wcc  # noqa: E402  (FLEET_SHARED)

LABEL = "build-ar-court-districts"
SOURCE = os.path.join(os.path.dirname(_HERE), "data", "source", "courts")
DIRECTORY = "aoc-circuit-judge-directory.tsv"
CIRCUIT_LAYER = "circuit-layer3-reading.tsv"
ORDER = "circuit-court-order.txt"
CIRCUIT_PAGE = "circuit-courts-page.txt"
ACT = "coa-act-1812.txt"
APPEALS_LAYER = "coa-layer2-reading.tsv"
POSITIONS = "coa-positions.tsv"

APPEALS = 7
APPEALS_JUDGES = 12
CIRCUITS = 28
# Every circuit judge the directory lists, 2026-10-16. 127 from January 1,
# 2027 (Act 220 of 2025), which is why WATCH.md carries a dated row.
CIRCUIT_JUDGES = 126
# The state layers were drawn on Census 2000 blocks and the county fabric is
# TIGER 2020, so their edges disagree by slivers. A county agrees with a layer
# when one unit holds at least this much of it and no other unit holds 1% or
# more. Measured 2026-10-16: the least any county gives its own unit is 98.57%
# (Mississippi County, whose remainder is river the old layer leaves uncovered)
# and the most any second unit holds is 0.77%.
LAYER_SHARE_FLOOR = 98.0
SLIVER_CEILING = 1.0

ORDINALS = ("first second third fourth fifth sixth seventh eighth ninth tenth "
            "eleventh twelfth thirteenth fourteenth fifteenth sixteenth "
            "seventeenth eighteenth nineteenth twentieth twenty-first "
            "twenty-second twenty-third").split()
DIRECTIONS = {"N": "North", "S": "South", "E": "East", "W": "West"}
# The card repeats these two sentences of the court system's own page.
CIRCUIT_PAGE_SAYS = (
    "Judicial candidates for circuit judge run in nonpartisan elections",
    "Circuit judges serve a six-year term.",
)
# The card repeats what the order says about its subdistricts.
ORDER_SAYS = (
    "for the purposes of election only",
    "All judges elected from the electoral sub-districts will exercise "
    "jurisdiction district-wide",
)


def lines(name):
    with open(os.path.join(SOURCE, name)) as fh:
        return [ln.rstrip("\n") for ln in fh if ln.strip() and not ln.startswith("#")]


def split_names(text):
    return sorted(p.strip() for p in re.split(r",\s*(?:and\s+)?|\s+and\s+", text)
                  if p.strip())


def ordinal(n):
    tens = n % 100
    suffix = ("th" if 11 <= tens <= 13
              else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))
    return "%d%s" % (n, suffix)


def circuit_unit(words):
    """"Eighth North Judicial Circuit" or "Eleventh West Judicial District"
    -> "8th North"; None for anything else."""
    m = re.match(r"^([A-Za-z-]+?)(?: (North|South|East|West))? Judicial "
                 r"(?:Circuit|District)s?$", words.strip())
    if not m or m.group(1).lower() not in ORDINALS:
        return None
    unit = ordinal(ORDINALS.index(m.group(1).lower()) + 1)
    return unit + (" " + m.group(2) if m.group(2) else "")


def layer_unit(code):
    """The circuit layer's "08N", "11W" or "1" -> "8th North", "11th West", "1st"."""
    m = re.match(r"^0?(\d{1,2})([NSEW]?)$", code)
    if not m:
        return None
    unit = ordinal(int(m.group(1)))
    return unit + (" " + DIRECTIONS[m.group(2)] if m.group(2) else "")


def read_layer(name, to_unit):
    """{county: unit} from a layer reading, each county checked to sit in one
    unit apart from slivers."""
    out = {}
    for ln in lines(name):
        county, code, share, others = (ln.split("\t") + [""])[:4]
        unit = to_unit(code)
        if unit is None:
            wcc.fail(LABEL, "%s: %s is in unit %r, which this builder does not "
                     "read" % (name, county, code))
        if float(share) < LAYER_SHARE_FLOOR:
            wcc.fail(LABEL, "%s: only %s%% of %s is in its unit %s, under the "
                     "%.0f%% that marks a whole county" % (name, share, county,
                                                          code, LAYER_SHARE_FLOOR))
        for part in filter(None, (p.strip() for p in others.split(";"))):
            other, pct = part.rsplit(" ", 1)
            if float(pct) >= SLIVER_CEILING:
                wcc.fail(LABEL, "%s: %s%% of %s is in %s as well as %s, so the "
                         "layer splits the county" % (name, pct, county, other, code))
        out[county] = unit
    return out


def read_circuits():
    by, divisions = collections.defaultdict(list), {}
    for ln in lines(DIRECTORY):
        county, words, divs = ln.split("\t")
        unit = circuit_unit(words)
        if unit is None:
            wcc.fail(LABEL, "the directory puts %s in %r, which this builder "
                     "does not read as a circuit" % (county, words))
        by[unit].append(county)
        divisions.setdefault(unit, {})[county] = [int(d) for d in divs.split(",")]
    counts = {}
    for unit, per_county in sorted(divisions.items()):
        sets = {tuple(v) for v in per_county.values()}
        if len(sets) != 1:
            wcc.fail(LABEL, "the directory lists different judges for different "
                     "counties of the %s circuit (%s), so it is not one "
                     "electorate of whole counties" % (unit, per_county))
        divs = list(next(iter(sets)))
        if divs != list(range(1, len(divs) + 1)):
            wcc.fail(LABEL, "the %s circuit's divisions are %s, not 1 to %d"
                     % (unit, divs, len(divs)))
        counts[unit] = len(divs)
    if len(by) != CIRCUITS:
        wcc.fail(LABEL, "the directory names %d circuits, expected %d"
                 % (len(by), CIRCUITS))
    if sum(counts.values()) != CIRCUIT_JUDGES:
        wcc.fail(LABEL, "the directory lists %d circuit judges and this builder "
                 "pins %d; read why before changing the pin (an eighth 19th West "
                 "judge takes office January 1, 2027)"
                 % (sum(counts.values()), CIRCUIT_JUDGES))
    layer = read_layer(CIRCUIT_LAYER, layer_unit)
    directory = {c: u for u, cs in by.items() for c in cs}
    if set(layer) != set(directory):
        wcc.fail(LABEL, "the circuit layer reading and the directory name "
                 "different counties")
    differ = sorted(c for c in directory if layer[c] != directory[c])
    if differ:
        wcc.fail(LABEL, "the state's circuit layer and the directory disagree "
                 "about %s" % ", ".join("%s (%s against %s)"
                                        % (c, layer[c], directory[c]) for c in differ))
    order = " ".join(lines(ORDER))
    for phrase in ORDER_SAYS:
        if phrase not in order:
            wcc.fail(LABEL, "%s no longer says %r, which the card repeats"
                     % (ORDER, phrase))
    m = re.search(r"creates electoral sub-districts with the (.*?) Judicial "
                  r"Districts for the purposes of election only", order)
    if not m:
        wcc.fail(LABEL, "%s no longer names the circuits with subdistricts" % ORDER)
    subdistricted = set()
    for words in split_names(m.group(1)):
        unit = circuit_unit(words + " Judicial District")
        if unit not in by:
            wcc.fail(LABEL, "the order names a circuit %r the directory does "
                     "not carry" % words)
        subdistricted.add(unit)
    page = " ".join(lines(CIRCUIT_PAGE))
    for phrase in CIRCUIT_PAGE_SAYS:
        if phrase not in page:
            wcc.fail(LABEL, "%s no longer says %r, which the card repeats"
                     % (CIRCUIT_PAGE, phrase))
    return by, counts, subdistricted


def read_appeals():
    by = {}
    for ln in lines(ACT):
        m = re.match(r"^\((\d)\) District (\d) shall be composed of (.*) "
                     r"counties[;.]?(?: and)?$", ln)
        if not m:
            continue
        if m.group(1) != m.group(2):
            wcc.fail(LABEL, "paragraph (%s) names District %s, so the quotation "
                     "is not read the way it was" % (m.group(1), m.group(2)))
        by[int(m.group(2))] = split_names(m.group(3))
    if sorted(by) != list(range(1, APPEALS + 1)):
        wcc.fail(LABEL, "%s names districts %s, expected 1 to %d"
                 % (ACT, sorted(by), APPEALS))
    layer = read_layer(APPEALS_LAYER, lambda code: int(code) if code.isdigit() else None)
    act = {c: d for d, cs in by.items() for c in cs}
    if set(layer) != set(act):
        wcc.fail(LABEL, "the appeals layer reading and the act name different "
                 "counties: %s" % ", ".join(sorted(set(layer) ^ set(act))))
    differ = sorted(c for c in act if layer[c] != act[c])
    if differ:
        wcc.fail(LABEL, "the state's appeals layer and Act 1812 disagree about "
                 "%s" % ", ".join("%s (%s against %s)" % (c, layer[c], act[c])
                                  for c in differ))
    positions = collections.Counter()
    for ln in lines(POSITIONS):
        district, _position = (ln.split("\t") + [""])[:2]
        positions[int(district)] += 1
    if sorted(positions) != sorted(by) or sum(positions.values()) != APPEALS_JUDGES:
        wcc.fail(LABEL, "the court's page lists %d positions in districts %s, "
                 "expected %d across districts 1 to %d"
                 % (sum(positions.values()), sorted(positions), APPEALS_JUDGES,
                    APPEALS))
    return by, positions


def tilings():
    appeals, positions = read_appeals()
    circuits, counts, subdistricted = read_circuits()
    print("%s: Act 1812's %d districts agree with the state layer county by "
          "county (%d judges); the directory's %d circuits of %d counties and %d "
          "judges agree with the state layer; subdistricts in %s"
          % (LABEL, len(appeals), sum(positions.values()), len(circuits),
             sum(len(v) for v in circuits.values()), sum(counts.values()),
             ", ".join(sorted(subdistricted))))
    rows_a = [(d, appeals[d], {"judge_count": positions[d]}) for d in sorted(appeals)]

    def key(unit):
        m = re.match(r"^(\d+)\D*(?: (\w+))?$", unit)
        return (int(m.group(1)), m.group(2) or "")

    rows_c = []
    for unit in sorted(circuits, key=key):
        extra = {"judge_count": counts[unit]}
        if unit in subdistricted:
            extra["subdistricts"] = True
        rows_c.append((unit, circuits[unit], extra))
    return [
        wcc.Tiling("ar-appeals-districts.json", "Court of Appeals district",
                   rows_a, APPEALS,
                   "Act 1812 of 2003, which names each district's counties, as "
                   "the state GIS office's metadata quotes it"),
        wcc.Tiling("ar-judicial-circuits.json", "judicial circuit", rows_c,
                   CIRCUITS,
                   "The Administrative Office of the Courts' circuit judge "
                   "directory, which lists the counties each judge serves, read "
                   "16 October 2026"),
    ]


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="verify the shipped files, write nothing")
    args = ap.parse_args()
    if args.check:
        wcc.check("ar", LABEL, tilings())
        print("%s: OK" % LABEL)
    else:
        wcc.build("ar", LABEL, tilings())


if __name__ == "__main__":
    main()
