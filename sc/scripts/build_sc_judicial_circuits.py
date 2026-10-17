#!/usr/bin/env python3
"""
Build sc/data/app/sc-judicial-circuits.json: South Carolina's 16 judicial
circuits, each a group of whole counties named in S.C. Code Section 14-5-610,
dissolved from the shipped county fabric.

    python3 sc/scripts/build_sc_judicial_circuits.py          # writes (needs shapely)
    python3 sc/scripts/build_sc_judicial_circuits.py --check  # offline, stdlib only

The dissolve, the partition gate and the offline check are
scripts/whole_county_courts.py, shared with the other states; this file says
how Section 14-5-610 is read.

WHO ELECTS WHOM. The General Assembly, not the voters, elects South Carolina's
circuit judges, by a joint public vote for six-year terms, and each must live
in the circuit they are elected for (S.C. Const. art. V, sec. 13). Section
14-5-610(B) sets how many are elected for each circuit, and (C) adds seven
elected from the state at large without regard to circuit. The judges then
rotate around the state as the Chief Justice directs (art. V, sec. 14), so the
judge hearing a case in a circuit need not be one of its own. The voters of
each circuit elect its solicitor, the prosecutor, to a four-year term (Section
1-7-310). So the circuit is drawn because it is the court's district and the
solicitor's electorate; Adam was asked on 2026-10-16 whether to draw it given
that legislators elect the judges, and the default, to draw it, stands until
he says otherwise.

WHAT IS READ. Both sections and the two constitutional sections are kept as
published, with their address and read date, in sc/data/source/courts/. Every
circuit paragraph's ordinal word is checked against its own paragraph number,
so a renumbered section cannot parse quietly into the wrong circuit, and every
circuit must receive exactly one judge count from (B). The judge count ships on
each circuit as `judge_count` (not `judges`, which the fleet's checks read as a
list of people). The card repeats who elects the judges, for how
long, that they rotate, and how the solicitor is chosen, so the build stops if
any of those sentences no longer reads the way the card says.
"""

import argparse
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)), "scripts"))

import whole_county_courts as wcc  # noqa: E402  (FLEET_SHARED)

LABEL = "build-sc-judicial-circuits"
SOURCE = os.path.join(os.path.dirname(_HERE), "data", "source", "courts")
STATUTE = "sc-code-14-5-610.txt"
SOLICITORS = "sc-code-1-7-310.txt"
CONSTITUTION = "sc-const-art5-13-14.txt"
# The constitution's words the card repeats, each of which must still be there.
CONSTITUTION_SAYS = (
    "For each circuit a judge or judges shall be elected by a joint public vote "
    "of the General Assembly",
    "He shall hold office for a term of six years",
    "during his continuance in office he shall reside in, the circuit of which "
    "he is judge",
    "all judges shall be systematically rotated throughout the State",
)
CIRCUITS = 16
AT_LARGE = 7
ORD = ("first second third fourth fifth sixth seventh eighth ninth tenth "
       "eleventh twelfth thirteenth fourteenth fifteenth sixteenth").split()
COUNTS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5, "Six": 6}


def text(name):
    with open(os.path.join(SOURCE, name)) as fh:
        return [ln.rstrip("\n") for ln in fh if ln.strip() and not ln.startswith("#")]


def parse():
    lines = text(STATUTE)
    if not lines[0].startswith("SECTION 14-5-610."):
        wcc.fail(LABEL, "%s does not open with Section 14-5-610" % STATUTE)
    circuits, judges, at_large = {}, {}, None
    for ln in lines:
        m = re.match(r"^\((\d+)\) The (\w+) circuit is composed of the counties of "
                     r"(.*)\.$", ln)
        if m:
            number, word = int(m.group(1)), m.group(2)
            if word not in ORD or ORD.index(word) + 1 != number:
                wcc.fail(LABEL, "paragraph (%d) names the %r circuit, so the "
                         "section has been renumbered" % (number, word))
            names = [p.strip() for p in re.split(r",\s*(?:and\s+)?|\s+and\s+",
                                                 m.group(3)) if p.strip()]
            circuits[number] = names
            continue
        if ln.startswith("(B) "):
            for count, which in re.findall(
                    r"(One|Two|Three|Four|Five|Six) judges? must be elected from "
                    r"the ([a-z, ]+?) circuits?\.", ln):
                for word in re.split(r",\s*(?:and\s+)?|\s+and\s+", which):
                    word = word.strip()
                    if word not in ORD:
                        wcc.fail(LABEL, "(B) names an unknown circuit %r" % word)
                    n = ORD.index(word) + 1
                    if n in judges:
                        wcc.fail(LABEL, "(B) gives the %s circuit two judge "
                                 "counts" % word)
                    judges[n] = COUNTS[count]
        if ln.startswith("(C) "):
            m = re.search(r"there must be (\w+) additional circuit judges elected "
                          r"by the General Assembly from the State at large", ln)
            if not m:
                wcc.fail(LABEL, "(C) no longer reads as the at-large judges")
            at_large = m.group(1)
    if sorted(circuits) != list(range(1, CIRCUITS + 1)):
        wcc.fail(LABEL, "the section names circuits %s, expected 1 to %d"
                 % (sorted(circuits), CIRCUITS))
    if sorted(judges) != list(range(1, CIRCUITS + 1)):
        wcc.fail(LABEL, "(B) sets judge counts for circuits %s, expected every "
                 "one of 1 to %d" % (sorted(judges), CIRCUITS))
    if at_large != "seven":
        wcc.fail(LABEL, "(C) sets %r at-large judges, and the card says %d"
                 % (at_large, AT_LARGE))
    sol = " ".join(text(SOLICITORS))
    if ("one solicitor for each judicial circuit, to be elected by the qualified "
            "electors of the circuit") not in sol or "term of four years" not in sol:
        wcc.fail(LABEL, "Section 1-7-310 no longer reads as one solicitor per "
                 "circuit elected by its voters for four years, which the card says")
    const = " ".join(text(CONSTITUTION))
    for phrase in CONSTITUTION_SAYS:
        if phrase not in const:
            wcc.fail(LABEL, "the constitution's article V no longer says %r, which "
                     "the card repeats" % phrase)
    return circuits, judges


def tilings():
    circuits, judges = parse()
    print("%s: Section 14-5-610 names %d circuits of %d counties, %d resident "
          "judges and %d at large" % (LABEL, len(circuits),
                                      sum(len(v) for v in circuits.values()),
                                      sum(judges.values()), AT_LARGE))
    rows = [(n, circuits[n], {"judge_count": judges[n]}) for n in sorted(circuits)]
    return [wcc.Tiling("sc-judicial-circuits.json", "judicial circuit", rows,
                       CIRCUITS, "South Carolina Code Section 14-5-610, which "
                       "names each circuit's counties")]


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="verify the shipped file, write nothing")
    args = ap.parse_args()
    if args.check:
        wcc.check("sc", LABEL, tilings())
        print("%s: OK" % LABEL)
    else:
        wcc.build("sc", LABEL, tilings())


if __name__ == "__main__":
    main()
