#!/usr/bin/env python3
"""
Build mi/data/app/mi-judges.json: the judges of each Court of Appeals district
and each of the 57 circuit courts, for the two court cards.

    python3 mi/scripts/build_mi_judges.py          # writes
    python3 mi/scripts/build_mi_judges.py --check  # offline: the shipped file must equal a rebuild

Nothing here fetches. www.courts.michigan.gov publishes `User-agent: *` /
`Disallow: /`, so no script reads it. On 2026-11-25, under Adam's ruling of
that day that a public page a site refuses to scripts may be read ONCE in his
own Chrome, the court's four Court of Appeals district pages and its trial
court directory were read there and kept in mi/data/source/courts/ (see
README.md). There is no weekly job; the re-read is in mi/WATCH.md.

THE DIRECTORY IS NOT SHIPPED AS READ:
  - 18 names it titles "Chief Judge" of a circuit are left out (NOT_CIRCUIT).
    None is in the Michigan Manual 2025-2026's table of circuit judges for that
    circuit, and none was appointed to it in any notice found. A chief judge is
    named by the Supreme Court and can be a probate or district judge of the
    same county, so the title alone does not make someone a circuit judge.
    Amy G. Gierhart is the 54th's judge and is also listed as the 52nd's chief.
  - Every name kept must have its surname in the Manual's table, or be an
    appointee in the notices file, or be named in DIRECTORY_ONLY with why.
    A re-read that brings in a name with no witness stops the build.
  - Two spellings follow the Manual, where the feed writes an apostrophe in
    place of an accent (SPELLING).
"""

import argparse
import json
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), "data", "source", "courts")
OUT = os.path.join(os.path.dirname(HERE), "data", "app", "mi-judges.json")
READ = "2026-11-25"
COA_TSV = "courts-mi-court-of-appeals-judges-%s.tsv" % READ
CIRCUIT_TSV = "courts-mi-circuit-judges-%s.tsv" % READ
NOTICES_TSV = "governor-court-notices-%s.tsv" % READ
MANUAL_TXT = "michigan-manual-2025-2026-pp471-472.txt"
COA_URL = "https://www.courts.michigan.gov/courts/court-of-appeals/judges/current-judges/"
CIRCUIT_URL = "https://www.courts.michigan.gov/trial-court-directory/"

NOT_CIRCUIT = {  # circuit -> directory names titled Chief Judge who are not this circuit's judges
    1: ["Michelle Snell Bianchi"], 2: ["Mabel Johnson Mayfield"], 5: ["William M. Doherty"],
    11: ["Beth A. Gibson"], 12: ["Fraser T. Strome"], 15: ["Kirk A. Kashian"],
    18: ["Mark E. Janer"], 21: ["Eric R. Janes"], 23: ["Richard E. Vollbach, Jr."],
    25: ["Cheryl L. Hill"], 27: ["David M. Glancy"], 29: ["Lisa Sullivan"],
    40: ["Laura Cheger Barnard"], 43: ["Carol M. Bealor"], 45: ["Robert Pattison"],
    51: ["Jeffrey C. Nellis"], 52: ["Amy G. Gierhart"], 55: ["Joshua M. Farrell"],
}
# Titled "Circuit Judge" by the directory, in neither the Manual nor a notice found.
# The Governor's search feed misses releases (README.md), and the directory is the
# court system's own current list, so they are kept.
DIRECTORY_ONLY = {3: ["Rula Aoun", "Robbie Gaines, Jr."]}
SPELLING = {"Kwame' LeRoy Rowe": "Kwamé LeRoy Rowe", "Andre' R. Borrello": "André R. Borrello"}
NOTES = {
    "coa3": ["Judge Christopher Yates resigned. On November 9, 2026 the Governor named "
             "Dan Osher to his seat, for a term ending January 1, 2029. The court's page "
             "did not list him yet on November 25, 2026."],
    "circuit1": ["The court's directory listed no judge of this circuit on November 25, 2026."],
}
JUDGE_NOTES = {(16, "Tracey A. Yokich"): "Retiring. The Governor named Jevona Fudge to "
               "this seat from December 14, 2026."}
ORDINAL = lambda n: "%d%s" % (n, "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


def fail(msg):
    sys.exit("build_mi_judges: FAIL: " + msg)


def rows(name):
    with open(os.path.join(SRC, name), encoding="utf-8") as fh:
        return [l.rstrip("\n").split("\t") for l in fh if l.strip() and not l.startswith("#")]


def fold(s):
    s = unicodedata.normalize("NFKD", s.replace("’", "'")).encode("ascii", "ignore").decode()
    return s.lower()


def surname(name):
    parts = [p for p in re.split(r"[ ,]+", name) if p and p not in ("Jr.", "III", "II")]
    return fold(parts[-1])


def build():
    with open(os.path.join(SRC, MANUAL_TXT), encoding="utf-8") as fh:
        manual = fold(fh.read()).replace(" -", "-")
    appointees = {}
    for date, court, who, _r, _s, _rel in rows(NOTICES_TSV):
        appointees.setdefault(court, set()).add(surname(who))

    coa = {}
    for d, name, ends, *note in rows(COA_TSV):
        role = {"chief judge": "Chief judge", "chief judge pro tem": "Chief judge pro tem"}.get((note or [""])[0])
        j = {"name": name, "termEnds": ends}
        if role:
            j["role"] = role
        coa.setdefault(d, {"judges": []})["judges"].append(j)
    if sorted(coa) != ["1", "2", "3", "4"] or sum(len(v["judges"]) for v in coa.values()) != 24:
        fail("the Court of Appeals pages listed 24 judges in 4 districts on %s" % READ)
    for d, v in coa.items():
        if NOTES.get("coa" + d):
            v["notes"] = NOTES["coa" + d]

    circuits, used_drop, used_spell, used_only = {}, set(), set(), set()
    for num, counties, judges in rows(CIRCUIT_TSV):
        n = int(num)
        kept = []
        for raw in judges.split("; "):
            name = raw.rstrip("*")
            if name in NOT_CIRCUIT.get(n, []):
                if not raw.endswith("*"):
                    fail("%s is left out as a chief judge but is not titled one" % name)
                used_drop.add((n, name))
                continue
            if name in SPELLING:
                used_spell.add(name)
                name = SPELLING[name]
            witnessed = re.search(r"\b%s\b" % re.escape(surname(name)), manual) or \
                surname(name) in appointees.get("circuit%d" % n, ())
            if name in DIRECTORY_ONLY.get(n, []):
                if witnessed:
                    fail("%s is in DIRECTORY_ONLY but has a witness; take it out" % name)
                used_only.add((n, name))
            elif not witnessed:
                fail("%s (%s Circuit) is in neither the Manual nor a notice" % (name, ORDINAL(n)))
            j = {"name": name}
            if JUDGE_NOTES.get((n, name)):
                j["note"] = JUDGE_NOTES[(n, name)]
            kept.append(j)
        kept.sort(key=lambda j: (surname(j["name"]), j["name"]))  # the feed's order is no order
        circuits[num] = {"judges": kept}
        if NOTES.get("circuit" + num):
            circuits[num]["notes"] = NOTES["circuit" + num]
    want = {(n, x) for n, xs in NOT_CIRCUIT.items() for x in xs}
    if used_drop != want:
        fail("NOT_CIRCUIT entries that match no directory row: %s" % sorted(want - used_drop))
    if used_spell != set(SPELLING):
        fail("SPELLING entries that match no directory row: %s" % sorted(set(SPELLING) - used_spell))
    if used_only != {(n, x) for n, xs in DIRECTORY_ONLY.items() for x in xs}:
        fail("DIRECTORY_ONLY entries that match no directory row")
    if sorted(circuits, key=int) != [str(i) for i in range(1, 58)]:
        fail("the directory must give all 57 circuits")
    total = sum(len(v["judges"]) for v in circuits.values())
    if total != 222:
        fail("222 circuit judges were kept on %s, not %d" % (READ, total))
    empty = [k for k, v in circuits.items() if not v["judges"]]
    if empty != ["1"]:
        fail("only the 1st Circuit had no judge listed on %s; now: %s" % (READ, empty))
    return {"read": READ, "courtOfAppealsUrl": COA_URL, "circuitUrl": CIRCUIT_URL,
            "courtOfAppeals": coa, "circuits": circuits}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    built = build()
    if ap.parse_args().check:
        with open(OUT, encoding="utf-8") as fh:
            if json.load(fh) != built:
                fail("shipped %s differs from a rebuild" % os.path.basename(OUT))
        print("build_mi_judges: OK")
        return
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(built, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print("wrote %s: 24 Court of Appeals judges, %d circuit judges" % (
        os.path.relpath(OUT), sum(len(v["judges"]) for v in built["circuits"].values())))


if __name__ == "__main__":
    main()
