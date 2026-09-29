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

A NUMBER THAT MOVES IS DERIVED RATHER THAN STATED, since 2026-09-29. A
declaration may carry a `name` in place of its `value`, the reader field writes
`{name}` where the number goes, and `build_coverage_gaps.py` ships the resolved
text — so a weekly figure is never typed and cannot go stale between refreshes.
The form, its bounded format spec, what it still cannot say, and WHY a constant
stays on `value` are all in `scripts/gap_counts.py`, which measures both forms
for both gates; they are not restated here, because two copies of one
explanation is the defect this module was written about. What lives here is the
RULES a declaration must satisfy — including the two that are this gate's own:
a `name` refuses `value` and `in` beside it, and a declaration no token
references FAILS exactly as a `value` whose number has left the prose does.

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
from gap_counts import (Stop, combined, entry_number, measured,     # noqa: E402
                        standalone, tokens_in)
# The selftest's claim/label cases call the evaluator directly, which is
# the split they exist to assert in both directions.
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


def fail(msg):
    failures.append(msg)


# THE MEASUREMENT MOVED OUT ON 2026-09-29 and this module imports it. It had to:
# `build_coverage_gaps.py` now resolves a `{name}` token into the shipped bytes,
# so it needs the same declaration measured — and it is imported BY this file
# rather than the other way round, so the code could not stay here without a
# cycle. `scripts/gap_counts.py` is the one reader; two readers of one question
# is where this fleet's recurring defect starts. What is still here is the
# RULES a declaration must satisfy, which is this gate's own subject.

def tokens_used(record, where):
    """Every token name the record's reader fields write.

    A field whose tokens are malformed reports through `fail` and contributes
    nothing, so a record with a broken token still gets its other declarations
    checked rather than the whole record going silent.
    """
    used = set()
    for key in READER_FIELDS:
        text = record.get(key)
        if not isinstance(text, str) or "{" not in text:
            continue
        got = tokens_in(text, where, key, fail)
        if got is None:
            continue
        used |= {t[0] for t in got}
    return used


def check_named(record, entry, where, used, seen, report):
    """A `name` declaration: measured, referenced, and stating no number itself.

    THE MIGRATION REFUSAL IS THE SECOND OF THE RULING'S THREE, and it is the
    vacuous-pass class turned on itself. A named declaration nothing references
    measures a file on every run and guards no text — it reads exactly like a
    held guard while guarding nothing, which is the state this gate exists to
    make impossible. Its `value`-form twin is the `standalone` test below: a
    declaration whose number has left the prose fails there for the same
    reason.
    """
    name = entry.get("name")
    if not isinstance(name, str) or not name.isidentifier():
        fail("%s: `name` must be an identifier, not %r" % (where, name))
        return
    if name in seen:
        fail("%s: declares the name %r a second time on this record — a token "
             "could resolve through either" % (where, name))
        return
    seen.add(name)
    # `value` and `in` are what a token REPLACES. Either one beside a name is a
    # second statement of something the token already says, and a second
    # statement that can disagree is the whole subject of this gate.
    for key, why in (("value", "the number the token resolves to"),
                     ("in", "which field states it, which the token's own "
                            "position says — and says for every field at once")):
        if key in entry:
            fail("%s: declares `name` and `%s` together, where `%s` is %s"
                 % (where, key, key, why))
            return
    if name not in used:
        fail("%s: declares the name %r and no reader field writes {%s} — a "
             "declaration nothing references measures a file on every run and "
             "guards no text, which reads exactly like a guard that is held"
             % (where, name, name))
        return
    got = entry_number(record, entry, where, fail)
    if got is None:
        return
    if report:
        print("  ok   %s: {%s} resolves to %d%s"
              % (where, name, got,
                 " (%d - %d)" % (entry["of"], entry["of"] - got)
                 if "of" in entry else ""))


def check_valued(record, entry, where, report):
    """A `value` declaration: the number as the prose writes it, checked against
    the file. Unchanged since #1137 but for the shared measurement."""
    if not isinstance(entry.get("value"), int):
        fail("%s: `value` must be an integer" % where)
        return
    field = entry.get("in")
    if field not in READER_FIELDS:
        fail("%s: `in` must name one of %s, not %r"
             % (where, ", ".join(READER_FIELDS), field))
        return
    if not standalone(entry["value"], record.get(field) or ""):
        fail("%s: declares %d and the record's %s does not state it — "
             "the declaration has drifted from the prose it guards"
             % (where, entry["value"], field))
        return
    try:
        got = measured(record, entry, where, fail)
    except Stop:
        return
    if got is None:
        return
    want = entry["of"] - got if "of" in entry else got
    if entry["value"] != want:
        fail("%s: the %s states %d, the source holds %d%s — "
             "update the record (and every other surface that "
             "repeats it) or fix the source"
             % (where, field, entry["value"], want,
                " (%d - %d)" % (entry["of"], got) if "of" in entry else ""))
    elif report:
        print("  ok   %s: %s states %d%s"
              % (where, field, entry["value"],
                 " (%d - %d)" % (entry["of"], got) if "of" in entry else ""))


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
            """combined() against the fixture; returns (value, [messages]).

            A LOCAL RECORDER, not the module global. Until 2026-09-29 this
            swapped `failures` out and back around the call, because the
            measurement read that global; it takes `fail` as an argument now,
            so the hack went with it.
            """
            said = []
            return combined(entry, "selftest", said.append, root=tmp), said

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

        # A combine-only key on a `file` entry does nothing, and an `overlap`
        # that does nothing reads exactly like a guard that is held. Checked
        # through measured(), because that is where the branch lives.
        def run_measured(entry):
            """measured() with a recording fail; returns its messages."""
            said = []
            try:
                measured({}, entry, "selftest", said.append, root=tmp)
            except Stop:
                pass
            return said

        said = run_measured({"file": "%s/a.json" % inst, "metric": "keys",
                             "overlap": 2})
        check(any("without `files`" in m for m in said),
              "a combine-only key on a non-combine entry is refused rather "
              "than silently doing nothing")

    # ---- the token form, all hermetic and all on `self` ------------------
    # NEGATIVE-TESTED 2026-09-29 by deleting each refusal in turn: the
    # reference check, the format bound, the unmatched-brace refusal, the
    # duplicate-name refusal, and the resolution itself. All five turn this
    # selftest red. THREE report a named failure and TWO raise a KeyError
    # instead — deleting the guard that proves a name is declared, or that a
    # spec is one of two, leaves the lookup it guarded undefined. Both are red
    # and only one is a message a reader can act on, which is recorded rather
    # than engineered around: the guards make those states unreachable, and
    # defending a second time against a state the line above forbids is how a
    # guard comes to look held while guarding nothing.
    #
    # AND THE FIRST INSTRUMENT USED TO MEASURE THOSE BREAKS COUNTED `FAIL`
    # LINES, so it reported 0 for the two that crash — a break that fully fails
    # the gate reading exactly like a break nothing catches. The honest
    # instrument is the EXIT CODE. That is the same defect, on the same
    # afternoon, as the loose comma pattern this form's docstring records.
    # EVERY CASE COUNTS THE RECORD'S OWN KEY, so the whole token block needs no
    # file and no temp directory: `self` is the one measurement form that reads
    # nothing off the tree, which makes these assertions about the GRAMMAR and
    # never about today's data. The counts 3 and 1234 are arbitrary and local;
    # nothing can make them pass by reaching a real file.
    from build_coverage_gaps import READER_MAX, reader_problems, resolve_all

    def rec(summary, counts, n=3, **extra):
        r = {"id": "fixture", "counties": ["c%d" % i for i in range(n)],
             "summary": summary, "counts": counts}
        r.update(extra)
        return r

    def resolved(record):
        """(shipped text or None, [messages]) for a record's summary."""
        out, said = resolve_all([record])
        return out[0].get("summary") if not said else None, said

    SELF = {"self": "counties"}

    got, said = resolved(rec("in {n} counties", [dict(SELF, name="n")]))
    check(got == "in 3 counties" and not said,
          "a token resolves to its declaration's own measurement")

    got, said = resolved(rec("in {n:,} counties", [dict(SELF, name="n")], n=1234))
    check(got == "in 1,234 counties" and not said,
          "the comma form writes 1,234 — the only number shape a `value` "
          "declaration cannot express at all")

    got, said = resolved(rec("in {n} of {total}", [dict(SELF, name="n")]))
    check(got is None and any("names no declaration" in m for m in said),
          "a token referencing no declaration is REFUSED rather than rendered "
          "unresolved or silently dropped")

    got, said = resolved(rec("in {n} counties",
                             [dict(SELF, name="n"), dict(SELF, name="n")]))
    check(got is None and any("a second time" in m for m in said),
          "the same name declared twice on one record is refused rather than "
          "the later one winning")

    got, said = resolved(rec("in {n} counties", [dict(SELF, name="bad name")]))
    check(got is None and any("must be an identifier" in m for m in said),
          "a `name` that is not an identifier is refused")

    got, said = resolved(rec("in {n counties", [dict(SELF, name="n")]))
    check(got is None and any("unmatched brace" in m for m in said),
          "an unmatched brace is refused — no reader field in this fleet uses "
          "one for anything else")

    got, said = resolved(rec("in {n:>10} counties", [dict(SELF, name="n")]))
    check(got is None and any("not an allowed format" in m for m in said),
          "a format spec outside {name} and {name:,} is refused, because a spec "
          "passed to format() is an unbounded mini-language in a prose file")

    # READER_MAX IS MEASURED ON WHAT A READER IS SERVED, both directions. The
    # second is the load-bearing one and it is Michigan's own record's shape:
    # measured 2026-09-29 its summary is 254 characters authored and 230
    # resolved, so holding the ceiling to the authored text would refuse the
    # first record this form exists for.
    LONG = "x" * (READER_MAX - 10)
    over = rec(LONG + " {n} " + "y" * 20, [dict(SELF, name="n")])
    out, said = resolve_all([over])
    check(not said, "the over-length fixture resolves before it is measured")
    problems = reader_problems("fixture", out[0])
    check(any("is %d characters" % len(out[0]["summary"]) in m for m in problems),
          "READER_MAX fails with the RESOLVED length, not the authored one")

    # Authored 247, resolved 235: over the ceiling in the source file and under
    # it on the card, which must PASS.
    under = rec("z" * 232 + " {averylongcount}", [dict(SELF, name="averylongcount")])
    check(len(under["summary"]) > READER_MAX,
          "the fixture is over the ceiling as authored (%d characters)"
          % len(under["summary"]))
    out, said = resolve_all([under])
    check(not said and len(out[0]["summary"]) <= READER_MAX,
          "and under it once resolved (%d characters)" % len(out[0]["summary"]))
    check(not reader_problems("fixture", out[0]),
          "so it passes — a ceiling on the authored text would refuse the first "
          "record the form exists for")

    # ---- the two refusals that are the gate's own, not the builder's --------
    def rules(record):
        """check_named over a record's declarations; returns its messages."""
        global failures
        keep, failures = failures, []
        used = tokens_used(record, "fixture")
        seen = set()
        for i, entry in enumerate(record.get("counts") or []):
            if "name" in entry:
                check_named(record, entry, "fixture counts[%d]" % i, used, seen, False)
        said, failures = failures, keep
        return said

    said = rules(rec("no token here", [dict(SELF, name="n")]))
    check(any("no reader field writes {n}" in m for m in said),
          "a named declaration nothing references is REFUSED — it measures a "
          "file every run and guards no text, which reads like a held guard")

    said = rules(rec("in {n} counties", [dict(SELF, name="n", value=3)]))
    check(any("`name` and `value` together" in m for m in said),
          "`value` beside a `name` is refused — two statements of one number is "
          "the whole subject of this gate")

    said = rules(rec("in {n} counties", [dict(SELF, name="n", **{"in": "summary"})]))
    check(any("`name` and `in` together" in m for m in said),
          "`in` beside a `name` is refused — the token's own position says "
          "where, and says it for every field at once")

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
            entries = record.get("counts") or []
            if not entries:
                continue
            rec_where = "%s/%s" % (metro, record["id"])
            used = tokens_used(record, rec_where)
            seen = set()
            for i, entry in enumerate(entries):
                where = "%s counts[%d]" % (rec_where, i)
                checked += 1
                if "name" in entry:
                    check_named(record, entry, where, used, seen, args.report)
                else:
                    check_valued(record, entry, where, args.report)

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
