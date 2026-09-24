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
instance and refuses if any shipped file moved.

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
import os
import re
import subprocess
import sys

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
    spec = {"file": os.path.basename(path), "metric": entry["metric"],
            "label": where}
    if "naming" in entry:
        spec["naming"] = entry["naming"]
    return measure_metric(REPO_ROOT, os.path.dirname(path), spec, fail_stop)


def check_shipped():
    """The declaration reaches no reader — proven, not asserted."""
    for metro, out in SHIPPED:
        cmd = [sys.executable, os.path.join(REPO_ROOT, "scripts", "build_coverage_gaps.py"),
               "--check", "--metro", metro, "--out", os.path.join(REPO_ROOT, out)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            fail("%s moved — a `counts` declaration must ship to nobody:\n    %s"
                 % (out, (r.stderr or r.stdout).strip().splitlines()[-1]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true",
                    help="print every declaration, not only the failures")
    args = ap.parse_args()

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
