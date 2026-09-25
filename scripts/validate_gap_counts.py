#!/usr/bin/env python3
"""A number a gap record states must equal the file it describes.

WHY THIS EXISTS. `ia-board-chair` told readers the board chair is named "in 43
of Iowa's 99 counties… In the other 56 it cannot" while the file held 38. It
said that for eleven days, on a page a reader opens, and nothing in this
repository compared the two. #1034 corrected the number and added no gate, so
the next Friday run could make it stale again in silence — exactly as it did
at 43. Both numbers were wrong together, which is why the complement is
checked here and not only the count.

IT DECLARES, IT NEVER INFERS, and that is the whole design. Measured
2026-09-24, the gaps block holds 153 numbers in its reader fields of which
THREE are backed by a shipped file; the rest are district numbers, years, area
codes, a parcel count, "911" and a distance in metres. Any rule that guessed
which number to check would be wrong about 150 of them.

AND THE COUNT ITSELF PROVES THE POINT. Two readers measured this corpus an
hour apart and got 152 and 153. Neither mis-measured: it holds exactly one
comma-grouped number, `1,659`, and a thousands-aware pattern reads it as one
where `\\b\\d{1,4}\\b` reads it as two. The figures differed because the RULE was
never stated — so a gate that enumerated numbers would be measuring its own
regex. This one is told which number it is looking at, and where.

THE DECLARATION lives on the record beside `blocker`, and ships to nobody:
`build_coverage_gaps.render()` copies an explicit FIELD_ORDER allowlist, so a
`counts` key reaches no reader and no data file. That is verified rather than
assumed — the `--check` below re-runs the builder's own check for every
instance and refuses when any of the six fails, which a negative test confirms
it does.

    "counts": [
      {"value": 38, "in": "summary", "file": "ia/data/app/x.json", "metric": "keys"},
      {"value": 61, "in": "summary", "file": "ia/data/app/x.json", "metric": "keys", "of": 99}
    ]

  value    the number as the prose writes it
  in       WHICH reader field states it, so the check is an exact membership
           test for one number rather than an enumeration of all of them
  file     repo-relative, explicit: nothing is inferred from the instance
  metric   the shared grammar in scripts/measured_metric.py, which
           build_history_page.py's measured tiles already use
  of       optional; the value is the COMPLEMENT, `of` minus the measurement
  self     in place of file+metric: the length of one of the record's own
           keys, which is how a record that counts its own `counties` is held
           to it

EVERY BRANCH FAILS LOUDLY AND NONE PASSES VACUOUSLY. A value above the file
and a value below it are both wrong. A declaration naming a file that is not
there, a metric outside the grammar, a reader field the record does not carry,
or a number that does not appear in the field it names, all FAIL rather than
quietly matching nothing — the property ACCEPTED_DROPS and EXPECTED_UNREACHABLE
already have. And a run that finds no declaration at all FAILS, because a gate
whose subject can silently become empty is one that reports success for having
looked at nothing.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_coverage_gaps import READER_FIELDS, load_gaps            # noqa: E402
from measured_metric import measure_metric                          # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Every instance whose shipped gaps file the --check pass re-verifies, with the
# --metro/--out pair each needs. Mirrors smoke-test.yml's own six runs; a key
# CI does not check still has to be proven unmoved, because the declaration
# must ship to nobody in EVERY instance rather than in the ones CI happens to
# look at.
SHIPPED = (("chicago", "il/data/app/coverage-gaps.json"),
           ("wisconsin", "wi/data/app/coverage-gaps.json"),
           ("iowa", "ia/data/app/coverage-gaps.json"),
           ("michigan", "mi/data/app/coverage-gaps.json"),
           ("nyc", "ny/data/app/coverage-gaps.json"),
           ("sf", "ca/data/app/coverage-gaps.json"))

failures = []


class Stop(Exception):
    """Raised instead of exiting, so one bad declaration does not end the run.

    scripts/measured_metric.py's evaluator calls `fail` and then CARRIES ON,
    because build_history_page.py's own `fail` exits the process. This module
    accumulates instead, so a fail that returned would let the evaluator walk
    past its own refusal and crash — which it did, with a traceback rather
    than a verdict, the first time a declaration named a metric outside the
    grammar. Every caller of the evaluator catches this, which is what lets a
    run report all of its failures at once.
    """


def fail(msg):
    failures.append(msg)


def fail_stop(msg):
    fail(msg)
    raise Stop(msg)


def standalone(value, text):
    """Is `value` written in `text` as a whole number rather than inside one?

    Bounded by non-digits on both sides, so a record stating 15 is not
    satisfied by the 15 inside 2015 or 150. This is a membership test for ONE
    number and never an enumeration, which is what keeps the tokenizer
    argument above out of the gate.
    """
    return re.search(r"(?<!\d)%d(?!\d)" % value, text) is not None


def measured(record, entry, where):
    """What the declaration says the number must equal, or None if it cannot say."""
    if "self" in entry:
        key = entry["self"]
        if key not in record:
            fail("%s: declares self=%r and the record has no such key" % (where, key))
            return None
        held = record[key]
        if not isinstance(held, (list, dict)):
            fail("%s: declares self=%r, which is a %s rather than something with a length"
                 % (where, key, type(held).__name__))
            return None
        return len(held)
    path = entry.get("file")
    if not path:
        fail("%s: declares neither `file` + `metric` nor `self`" % where)
        return None
    full = os.path.join(REPO_ROOT, path)
    if not os.path.exists(full):
        fail("%s: names %s, which is not in the tree" % (where, path))
        return None
    if "metric" not in entry:
        fail("%s: names %s and no `metric` to measure it by" % (where, path))
        return None
    # measure_metric joins root/inst/file, so the repo-relative path is split
    # to keep its own failure messages readable.
    # `claim` IS EMPTY ON PURPOSE. measure_metric tests a caller's own words
    # for PERSON_WORDS and, finding one on a `keys` metric, demands a `naming`
    # key saying the keys name people. A stat tile's label is such a claim; a
    # gap record's `counts` entry is not — it asserts only that a number in the
    # prose equals a measurement, and the only words it could offer are the
    # record's ID, which NAMES AN ABSENCE. Passing `where` here made
    # `ia-municipal-officeholders` demand that 939 CITY contact rows declare
    # they name people, and 18 record ids across four instances trip the same
    # way, while `ia-board-chair`'s 38 keys ARE 38 named chairs and pass
    # unchecked. A record that wants the comparison gives `naming` and gets it.
    spec = {"file": os.path.basename(path), "metric": entry["metric"],
            "label": where, "claim": ""}
    if "naming" in entry:
        spec["naming"] = entry["naming"]
    return measure_metric(REPO_ROOT, os.path.dirname(path), spec, fail_stop)


def check_shipped():
    """The declaration reaches no reader — proven by negative test, not asserted.

    NEGATIVE-TESTED 2026-09-24 by adding `counts` to the builder's FIELD_ORDER:
    all six instances failed. They failed by CRASHING, not by the file moving —
    `render()` copies the allowlist with `e[key]`, so the first record WITHOUT a
    `counts` key raises `KeyError: 'counts'` before a byte is written. A moved
    file is the other path, and it is the one a leak would take only if EVERY
    record carried a declaration. Re-running the builder's own check catches
    both; diffing the shipped file would catch only the second.
    """
    for metro, out in SHIPPED:
        cmd = [sys.executable, os.path.join(REPO_ROOT, "scripts", "build_coverage_gaps.py"),
               "--check", "--metro", metro, "--out", os.path.join(REPO_ROOT, out)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            fail("%s: the builder refused or the file moved — a `counts` "
                 "declaration must ship to nobody:\n    %s"
                 % (out, (r.stderr or r.stdout).strip().splitlines()[-1]))


def _selftest():
    """The `claim` split, both directions, against a FIXTURE and never the tree.

    WHY IT EXISTS. The 2026-09-25 fix is invisible to every other gate here.
    Eighteen record ids across four instances contain a PERSON_WORD, and today
    exactly one of them declares a count — through `self`, which never reaches
    measure_metric at all. So reverting the split would leave this gate green
    until somebody gave one of the other seventeen a `file` + `metric`, and then
    it would refuse a true declaration for a reason no reader could act on.

    Both directions are asserted, because the fix must not weaken the check it
    narrows: a caller whose OWN WORDS claim people while counting keys is still
    refused, and a caller that makes no such claim is not.

    IT READ THE SHIPPED FILES UNTIL 2026-09-25 AND THAT WAS THE WRONG CALL. Its
    two value assertions were `== 38` on ia-county-board-chairs.json and `== 939`
    on ia-city-contact.json, so the weekly chair refresh — five Iowa counties
    starting to name a chair, 38 to 43, the good outcome that roster exists to
    produce — made this gate's own proof of correctness FAIL on the bot PR while
    passing on main. **A selftest that a data change can break is not a selftest
    of the code**, and the second assertion was one new Iowa city away from the
    same thing. Both now run against a two-file fixture in a temp directory.

    THE FIXTURE COUNTS ARE 7 AND 3 ON PURPOSE. No real file in this fleet holds
    either — Iowa has 99 counties and 939 cities — so if anybody points these
    cases back at the tree the assertions FAIL rather than passing by luck. That
    is the whole proof of hermeticity: the expected values could only have come
    from the fixture.
    """
    failures = []

    def check(cond, msg):
        if not cond:
            failures.append(msg)
        print("  %s %s" % ("ok  " if cond else "FAIL", msg), file=sys.stderr)

    with tempfile.TemporaryDirectory() as tmp:
        inst = os.path.join("fixture", "data", "app")
        os.makedirs(os.path.join(tmp, inst))

        def write(name, obj):
            with open(os.path.join(tmp, inst, name), "w", encoding="utf-8") as fh:
                json.dump(obj, fh)

        # The ia-city-contact SHAPE: keyed by place, naming nobody.
        CITIES, N_CITIES = "cities.json", 7
        write(CITIES, {"190%04d" % i: {"city": "Fixture City %d" % i,
                                       "phone": "515-000-0000",
                                       "website": "example.invalid"}
                       for i in range(1, N_CITIES + 1)})
        # The ia-county-board-chairs SHAPE: keyed by county, every one naming a
        # `chair`, which is what the opt-in comparison looks for.
        CHAIRS, N_CHAIRS = "chairs.json", 3
        write(CHAIRS, {"191%02d" % i: {"county": "Fixture County %d" % i,
                                       "chair": "A Person %d" % i}
                       for i in range(1, N_CHAIRS + 1)})

        def run(spec):
            """measure_metric with a recording fail; returns (value, [messages])."""
            said = []
            val = measure_metric(tmp, inst, spec, said.append)
            return val, said

        # A. STILL REFUSED. A stat tile's label IS its claim, so a tile counting
        #    keys while its words say "seats" must still be made to declare where
        #    its people are. This is the check that caught two real ILGA tiles.
        val, said = run({"file": CITIES, "metric": "keys",
                         "label": "%d Iowa city seats with their member" % N_CITIES})
        check(len(said) == 1 and "needs a \"naming\" key" in said[0],
              "a caller whose own label claims people is still refused without naming")

        # B. NO LONGER REFUSED. A gap record's counts entry passes claim="" because
        #    the only words it has are its ID, which names an ABSENCE.
        val, said = run({"file": CITIES, "metric": "keys", "claim": "",
                         "label": "iowa/ia-municipal-officeholders counts[0]"})
        check(val == N_CITIES and not said,
              "a gap record whose ID merely contains a person word counts its %d "
              "cities without being asked to claim they are people" % N_CITIES)

        # C. THE OPT-IN STILL WORKS, and is driven by `naming` rather than by the
        #    words, so a caller with no person word in sight can still ask for it.
        val, said = run({"file": CHAIRS, "metric": "keys", "claim": "",
                         "label": "opt-in", "naming": "chair"})
        check(val == N_CHAIRS and not said,
              "a caller that opts in with naming gets the comparison and passes "
              "when every key names somebody")

        # D. AND THE OPT-IN STILL CATCHES A FALSE ONE. Same naming, wrong file.
        val, said = run({"file": CITIES, "metric": "keys", "claim": "",
                         "label": "opt-in on the wrong file", "naming": "chair"})
        check(any("names anybody under it" in m for m in said),
              "an opt-in naming that no record satisfies is still refused")

    print("selftest: %d failure(s)" % len(failures), file=sys.stderr)
    return 1 if failures else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true",
                    help="print every declaration, not only the failures")
    ap.add_argument("--selftest", action="store_true",
                    help="assert the claim/label split in both directions, offline")
    args = ap.parse_args()
    if args.selftest:
        sys.exit(_selftest())

    checked = 0
    for metro, gaps in sorted(load_gaps().items()):
        for record in gaps:
            for i, entry in enumerate(record.get("counts") or []):
                where = "%s/%s counts[%d]" % (metro, record["id"], i)
                checked += 1
                if not isinstance(entry.get("value"), int):
                    fail("%s: `value` must be an integer" % where)
                    continue
                field = entry.get("in")
                if field not in READER_FIELDS:
                    fail("%s: `in` must name one of %s, not %r"
                         % (where, ", ".join(READER_FIELDS), field))
                    continue
                if not standalone(entry["value"], record.get(field) or ""):
                    fail("%s: declares %d and the record's %s does not state it — "
                         "the declaration has drifted from the prose it guards"
                         % (where, entry["value"], field))
                    continue
                try:
                    got = measured(record, entry, where)
                except Stop:
                    continue
                if got is None:
                    continue
                want = entry["of"] - got if "of" in entry else got
                if entry["value"] != want:
                    fail("%s: the %s states %d, the source holds %d%s — "
                         "update the record (and every other surface that "
                         "repeats it) or fix the source"
                         % (where, field, entry["value"], want,
                            " (%d - %d)" % (entry["of"], got) if "of" in entry else ""))
                elif args.report:
                    print("  ok   %s: %s states %d%s"
                          % (where, field, entry["value"],
                             " (%d - %d)" % (entry["of"], got) if "of" in entry else ""))

    if not checked:
        fail("no gap record declares a `counts` entry, so this gate measured "
             "nothing. It is wired into CI and must have a subject: either a "
             "declaration was dropped, or load_gaps() stopped reaching the block.")
    check_shipped()

    if failures:
        for msg in failures:
            print("validate-gap-counts: FAIL — %s" % msg, file=sys.stderr)
        sys.exit(1)
    print("validate-gap-counts: OK — %d stated count(s) agree with the files they "
          "describe, and no shipped coverage-gaps.json moved" % checked)


if __name__ == "__main__":
    main()
