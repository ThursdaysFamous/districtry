# South Carolina judicial circuits: the statute and constitution text read

These files are what `sc/scripts/build_sc_judicial_circuits.py` reads to draw
South Carolina's 16 judicial circuits. Every circuit is a set of whole
counties named in statute, so the statute is the boundary: the builder
dissolves the county fabric this instance already ships
(`sc/data/app/state-counties.json`), and no map is read. All three were read on
2026-10-16 from the South Carolina Legislature's own site, scstatehouse.gov,
with this project's own client, after reading robots.txt, which permits them.

| file | what it settles |
|---|---|
| `sc-code-14-5-610.txt` | the 16 circuits county by county (subsection A), how many judges are elected for each circuit (B), and the seven more elected from the state at large (C) |
| `sc-code-1-7-310.txt` | one solicitor for each circuit, elected by the circuit's voters for four years |
| `sc-const-art5-13-14.txt` | Article V, section 13: each circuit's judges are elected by a joint public vote of the General Assembly for six years and must live in the circuit; section 14: the judges are rotated around the state |

**WHAT THE CARD DOES WITH IT.** South Carolina's voters do not elect circuit
judges: the General Assembly does, and the judges rotate, so the judge hearing
a case in a circuit need not be one of its own. The circuit is drawn because it
is the court's district, the district its resident judges must live in, and the
solicitor's electorate. The card says all of that, and the builder stops if any
sentence it repeats no longer reads that way in these files.

Adam was asked on 2026-10-16 whether to draw circuits on that reading; the
default, to draw them, stands until he says otherwise.
