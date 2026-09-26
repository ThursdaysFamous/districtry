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

A NUMBER THAT IS A UNION ACROSS FILES gets `files` + `combine` instead, added
2026-09-26 after TWO records in two days could not be declared without it:
Iowa's 106 named cities (4 publishing their own officials + 102 whose county
does) and Illinois's 226 libraries naming a board (173 filing + 53 from their
own site). Both had to have their prose reworded to gate anything at all,
which is the tell that the grammar was short rather than the records odd.

    {"value": 106, "in": "summary", "combine": "union", "field": "members",
     "files": ["ia/data/app/ia-city-officials.json",
               "ia/data/app/ia-county-city-officials.json"]}

  files    two or more repo-relative paths; one file is what `file` already says
  combine  STATED, never inferred, and "union" is the only one — a second
           combine is a decision somebody makes, not a default
  field    the key a record must carry, non-empty, to be counted
  under    optional: the key the records nest under (Illinois's libraries do,
           Iowa's cities do not); naming one a file lacks FAILS
  overlap  optional: how many keys the files share, which must be DECLARED
           before a union is allowed to include them

AN ENTRY NAMES EXACTLY ONE OF `self`, `file` OR `files`. Two would be resolved
by whichever branch `measured` tests first, which is a rule no reader could
see from the entry.

THREE THINGS THE COMBINE REFUSES, each earned by a measurement rather than
anticipated. A named field ABSENT from a named file fails instead of
contributing nothing: Illinois publishes its 79 per-county library files under
five different name keys, and a reader keyed on one spelling returns zero for
the files it misses and reports a clean total that is silently short — one
defect that produced three different answers (599, 416, 373) to what looked
like one question. An UNDECLARED OVERLAP fails, because a union over
overlapping sources double-counts, which is the same defect the union exists
to fix one level up. And every path is re-read from the tree on every run, so
an entry naming a file that has left FAILS as an orphan, the property
ACCEPTED_DROPS and EXPECTED_UNREACHABLE already have.

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
    """What the declaration says the number must equal, or None if it cannot say.

    THREE FORMS, AND NAMING TWO IS AN ERROR RATHER THAN A PRECEDENCE: `self`
    counts one of the record's own keys, `file` + `metric` measures one file,
    and `files` + `combine` measures several. An entry carrying two of them
    would be read by whichever branch this function tests first, which is a
    rule nobody could see from the entry.
    """
    forms = [k for k in ("self", "file", "files") if k in entry]
    if len(forms) > 1:
        fail("%s: declares %s together — an entry names exactly one of `self`, "
             "`file` or `files`" % (where, " and ".join(repr(f) for f in forms)))
        return None
    if "files" in entry:
        return combined(entry, where)
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


def _records(root, path, under, where):
    """The {key: record} mapping a combine counts over, or None having failed."""
    full = os.path.join(root, path)
    if not os.path.exists(full):
        fail("%s: names %s, which is not in the tree" % (where, path))
        return None
    with open(full, encoding="utf-8") as fh:
        doc = json.load(fh)
    if under is not None:
        if not isinstance(doc, dict) or under not in doc:
            fail("%s: names `under`=%r and %s has no such key — a combine may "
                 "not count a file whose records it cannot find"
                 % (where, under, path))
            return None
        doc = doc[under]
    if not isinstance(doc, dict):
        fail("%s: %s holds a %s where a combine needs an object keyed by source"
             % (where, path, type(doc).__name__))
        return None
    return doc


def _keys_with_field(root, path, field, under, where):
    """Keys in `path` whose record carries a non-empty `field`.

    FAILS ON ZERO RATHER THAN CONTRIBUTING NOTHING, which is the whole reason
    this function exists rather than a comprehension at the call site. Illinois
    publishes its 79 per-county library files under FIVE different name keys —
    72 use `library`, and Boone and Grundy use `district`, Kendall `library`,
    Macon `Library`, Rock Island `library_di`, Stark `name`, Woodford `code`
    — so a reader keyed on one spelling returns ZERO for the files it misses
    and reports a clean total that is silently short. Measured 2026-09-26, that
    one defect produced three different answers (599, 416, 373) to what looked
    like one question. A union that let an absent field contribute nothing
    would institutionalise exactly that.
    """
    doc = _records(root, path, under, where)
    if doc is None:
        return None
    got = {k for k, v in doc.items() if isinstance(v, dict) and v.get(field)}
    if not got:
        fail("%s: no record in %s carries a non-empty %r, so it would "
             "contribute nothing to the union in silence — name the field the "
             "file actually uses, or drop the file from `files`"
             % (where, path, field))
        return None
    return got


def combined(entry, where, root=None):
    """A `files` + `combine` declaration's measurement, or None having failed.

    THE GRAMMAR IS DELIBERATELY ONE COMBINE. `union` is what two records in two
    days needed — Iowa's 4 + 102 named cities and Illinois's 173 + 53 libraries
    naming a board — and each is only correct because the two sides are
    DISJOINT. A silent overlap turns a union into a double count, which is the
    same defect the union exists to fix one level up, so an overlap must be
    declared before it is allowed.
    """
    root = REPO_ROOT if root is None else root
    files = entry["files"]
    if not isinstance(files, list) or len(files) < 2:
        fail("%s: `files` must list at least two paths — one file is what "
             "`file` + `metric` already says" % where)
        return None
    if entry.get("combine") != "union":
        fail("%s: `combine` must be stated as \"union\", not %r — the vocabulary "
             "is deliberately tiny and a new combine is a decision, not a default"
             % (where, entry.get("combine")))
        return None
    field = entry.get("field")
    if not field:
        fail("%s: a combine needs `field`, the key a record must carry to be "
             "counted" % where)
        return None
    under = entry.get("under")

    sets = {}
    for path in files:
        got = _keys_with_field(root, path, field, under, where)
        if got is None:
            return None
        sets[path] = got

    paths = list(sets)
    overlap = set()
    for i in range(len(paths)):
        for j in range(i + 1, len(paths)):
            overlap |= sets[paths[i]] & sets[paths[j]]
    declared = entry.get("overlap", 0)
    if len(overlap) != declared:
        fail("%s: the named files share %d key(s) carrying %r and the entry "
             "declares %d — a union over overlapping sources double-counts "
             "unless the overlap is stated%s"
             % (where, len(overlap), field, declared,
                "" if overlap else ""))
        return None

    union = set()
    for got in sets.values():
        union |= got
    return len(union)


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


    # ---- the `files` + `combine` widening, all hermetic ------------------
    # COUNTS ARE 11 / 5 / 2 ON PURPOSE, the same hermeticity proof the cases
    # above use: no real file in this fleet holds them, so an assertion that
    # passed by reaching the tree would fail instead of passing by luck.
    with tempfile.TemporaryDirectory() as tmp:
        inst = os.path.join("fixture", "data", "app")
        os.makedirs(os.path.join(tmp, inst))

        def write(name, obj):
            with open(os.path.join(tmp, inst, name), "w", encoding="utf-8") as fh:
                json.dump(obj, fh)

        A, B = "%s/a.json" % inst, "%s/b.json" % inst
        NESTED, EMPTY = "%s/nested.json" % inst, "%s/empty.json" % inst
        # A holds 11 keys with `members`; B holds 5, of which 2 are also in A.
        write("a.json", {"a%02d" % i: {"members": ["x"]} for i in range(11)})
        write("b.json", {"a09": {"members": ["x"]}, "a10": {"members": ["x"]},
                         "b1": {"members": ["x"]}, "b2": {"members": ["x"]},
                         "b3": {"members": ["x"]}})
        write("nested.json", {"generated": "x",
                              "rows": {"n%d" % i: {"members": ["x"]} for i in range(3)}})
        # The five-keys shape: real records, and not one carrying `members`.
        write("empty.json", {"e%d" % i: {"heads": ["x"]} for i in range(4)})

        def run(entry):
            """combined() against the fixture; returns (value, [messages])."""
            global failures
            keep, failures = failures, []
            val = combined(entry, "selftest", root=tmp)
            said, failures = failures, keep
            return val, said

        base = {"combine": "union", "field": "members"}

        val, said = run(dict(base, files=[A, B], overlap=2))
        check(val == 14 and not said,
              "a union of 11 and 5 sharing a declared 2 measures 14")

        val, said = run(dict(base, files=[A, B]))
        check(val is None and any("share 2 key(s)" in m for m in said),
              "the SAME union with the overlap undeclared is refused, because a "
              "silent overlap double-counts")

        val, said = run(dict(base, files=[A, B], overlap=1))
        check(val is None and any("declares 1" in m for m in said),
              "an overlap declared at the wrong number is refused too")

        val, said = run(dict(base, files=[A, EMPTY], overlap=0))
        check(val is None and any("contribute nothing to the union in silence" in m
                                  for m in said),
              "a file where no record carries the field FAILS rather than "
              "contributing nothing — the five-keys defect")

        val, said = run(dict(base, files=[NESTED, B], under="rows"))
        check(val is None and any("has no such key" in m for m in said),
              "`under` naming a key one of the files lacks is refused")

        val, said = run({"combine": "union", "field": "members",
                         "files": [A, "%s/gone.json" % inst]})
        check(val is None and any("not in the tree" in m for m in said),
              "a combine naming a path that has left the tree is refused")

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
