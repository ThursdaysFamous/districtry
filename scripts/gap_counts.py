#!/usr/bin/env python3
"""What a gap record's `counts` declaration measures, and how a token resolves.

WHY THIS IS A MODULE AND NOT A SECOND COPY. Until 2026-09-29 the measurement
lived inside `validate_gap_counts.py` alone, which was right while a
declaration only ever CHECKED a number somebody had typed. A token changes the
subject: `build_coverage_gaps.py` now has to resolve `{chairs}` into the
shipped bytes, so it needs the same question answered — and it is imported BY
the gate rather than the other way round, so the measurement could not stay
there without a cycle. Two readers of one question is where this fleet's
recurring defect starts, so the measurement moved here and both callers import
it. `validate_gap_counts.py`'s own docstring is still the record of WHY the
declaration exists; this file is the record of what it measures.

WHAT MOVED AND WHAT DID NOT. `measured`, `combined`, their two helpers and
`standalone` are that module's code, lifted with their docstrings intact
because those docstrings are measurements — the five library name keys, the
three answers 599/416/373, what the overlap guard actually buys. The one
change is that `fail` is an argument rather than a module global, the same lift
`measured_metric.py` already took from `build_history_page.py`. The proof it was
faithful is that the shipped `coverage-gaps.json` of all six instances comes
back byte-identical.

THE TOKEN FORM, ruled by the manager on 2026-09-26 and released 2026-09-29.
The design offered was a bare token resolved at render time, and the ruling is
that this is the expensive mistake rather than a theoretical one: Illinois's
382 had three defensible answers that week (599 features, 416 distinct across
79 files, 373 across the 72 dispatched), and a bare token would have rendered
one of them confidently and forever with nobody able to see which. So DERIVE
FROM A DECLARATION, NEVER INSTEAD OF ONE. The declaration stays exactly where
it was, states the same file and metric, and gains a `name`; the authored field
writes `{name}` where the number went; and the builder ships the resolved text.
The question being asked stays visible in the record.

    "summary": "... in {chairs} of Iowa's {counties} counties ... the other {without} ...",
    "counts": [
      {"name": "chairs",   "file": "ia/data/app/ia-county-board-chairs.json", "metric": "keys"},
      {"name": "counties", "file": "ia/data/app/ia-county-officers.json",     "metric": "keys"},
      {"name": "without",  "file": "ia/data/app/ia-county-board-chairs.json", "metric": "keys", "of": 99}
    ]

  name     optional; its presence is what makes an entry a token declaration
  value    the number as the prose writes it — REFUSED beside `name`, because
           two statements of one number are what this whole gate exists against
  in       which reader field states it — REFUSED beside `name`, because the
           token's own position says where, and says it in as many fields as
           the record likes. That is what makes a record SMALLER on migrating:
           Michigan states one number three times as three declarations, and
           under a name it is one declaration referenced from three fields.

DERIVE WHAT MOVES, STATE WHAT DOES NOT — Michigan's rule, 2026-09-26, and the
reason `name` is optional rather than the only form. Its 52 and 31 shift every
tranche, so a token is right for those. Its 83 is a constant, and if
`state-counties.json` ever holds 82 then `value: 83` FAILS and somebody looks,
where `{counties}` would render "All 82 Michigan counties now name a
commissioner" with every gate green. DERIVATION TURNS A LOUD FAILURE INTO A
QUIET SENTENCE THAT IS TRUE ABOUT A BROKEN FILE. Both forms are allowed on one
record for that reason.

THE FORMAT SPEC IS BOUNDED TO TWO VALUES, `{name}` and `{name:,}`, and nothing
else. Passing a spec through to `format()` would accept `{name:>10,.2f}` — an
unbounded formatting mini-language in a prose file with nothing gating it —
where every other part of this vocabulary is deliberately tiny. The comma form
exists because a declaration on the `value` form cannot express a number of
1,000 or more at all: `standalone()` matches bare digits, so `1,659` in a
reader field can never be declared. MEASURED 2026-09-29 ACROSS THE SHIPPED
BLOCK, THAT IS EXACTLY ONE NUMBER — `lasalle-board-districts-stale`'s 1,659 —
and the figure is stated with its method because a looser pattern answers 19.
`\\d[\\d,]*` counts the trailing punctuation in `2022,` and `2018,` as a
thousands separator; the correct test is a comma followed by exactly three
digits. Two instruments agreeing is not a measurement when they share a defect.

WHAT THIS GRAMMAR STILL CANNOT SAY, stated rather than left to be discovered.
`of` is an integer literal and may not name another declaration, so a record
whose complement is taken over a measured total types that total twice —
`ia-board-chair` declares `{counties}` at 99 AND carries `"of": 99`. There the
literal is protected by the sibling declaration, which fails loudly if the file
ever holds 98, but that is luck rather than design: a record with an `of` and
no matching declaration has an unchecked number in it. Widening `of` to take a
name is a second decision and a second entry in a vocabulary kept small on
purpose, so it is recorded here instead of taken.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from measured_metric import measure_metric                          # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# A token is a brace pair holding a name and an optional format spec. The body
# excludes braces so a stray `{` cannot be swallowed by a match that spans it —
# which is what lets the leftover-brace refusal below see one at all.
TOKEN_RE = re.compile(r"\{([^{}]*)\}")
# The whole of the format vocabulary. Bounded on purpose; see the docstring.
SPECS = {"": "{:d}", ",": "{:,d}"}


class Stop(Exception):
    """Raised instead of exiting, so one bad declaration does not end the run.

    `measured_metric.py`'s evaluator calls `fail` and then CARRIES ON, because
    `build_history_page.py`'s own `fail` exits the process. Both callers here
    accumulate instead, so a fail that merely returned would let the evaluator
    walk past its own refusal and crash — which it did, with a traceback rather
    than a verdict, the first time a declaration named a metric outside the
    grammar. Every caller catches this, which is what lets a run report all of
    its failures at once.
    """


def _stopper(fail):
    def fail_stop(msg):
        fail(msg)
        raise Stop(msg)
    return fail_stop


def standalone(value, text):
    """Is `value` written in `text` as a whole number rather than inside one?

    Bounded by non-digits on both sides, so a record stating 15 is not
    satisfied by the 15 inside 2015 or 150. This is a membership test for ONE
    number and never an enumeration, which is what keeps the tokenizer
    argument in `validate_gap_counts.py`'s docstring out of the gate.
    """
    return re.search(r"(?<!\d)%d(?!\d)" % value, text) is not None


def _records(root, path, under, where, fail):
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


def _keys_with_field(root, path, field, under, where, fail):
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
    doc = _records(root, path, under, where, fail)
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


def combined(entry, where, fail, root=None):
    """A `files` + `combine` declaration's measurement, or None having failed.

    THE GRAMMAR IS DELIBERATELY ONE COMBINE. `union` is what two records in two
    days needed — Iowa's 4 + 102 named cities and Illinois's 173 + 53 libraries
    naming a board.

    WHAT THE OVERLAP GUARD ACTUALLY BUYS, stated precisely because the obvious
    rationale is wrong about this code: the measurement below is a TRUE union
    of key sets, so it never double-counts and an undeclared overlap could not
    make it. The author's arithmetic is what overlaps break. Both records got
    their number by adding two counts in their head, and that addition is only
    right while the sides are disjoint. Two things follow. A value that stops
    matching is caught by the value check anyway, but with a message about the
    prose rather than about the cause. And an overlap can APPEAR WITHOUT MOVING
    THE UNION — one file gaining a key the other already had, while another key
    arrives elsewhere — which no value check can see, because the number is
    still right and the sources have quietly stopped meaning what they meant.
    So the overlap is declared, and a change to it is a failure a reader can
    act on.
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
        got = _keys_with_field(root, path, field, under, where, fail)
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
             "declares %d — the union itself is measured and stays right, but "
             "the prose number was reached by adding the sides together, which "
             "only holds while they are disjoint. State the overlap."
             % (where, len(overlap), field, declared))
        return None

    union = set()
    for got in sets.values():
        union |= got
    return len(union)


def measured(record, entry, where, fail, root=None):
    """What the declaration says the number must equal, or None if it cannot say.

    THREE FORMS, AND NAMING TWO IS AN ERROR RATHER THAN A PRECEDENCE: `self`
    counts one of the record's own keys, `file` + `metric` measures one file,
    and `files` + `combine` measures several. An entry carrying two of them
    would be read by whichever branch this function tests first, which is a
    rule nobody could see from the entry.
    """
    root = REPO_ROOT if root is None else root
    fail_stop = _stopper(fail)
    forms = [k for k in ("self", "file", "files") if k in entry]
    if len(forms) > 1:
        fail("%s: declares %s together — an entry names exactly one of `self`, "
             "`file` or `files`" % (where, " and ".join(repr(f) for f in forms)))
        return None
    if "files" in entry:
        return combined(entry, where, fail, root=root)
    stray = [k for k in ("combine", "field", "under", "overlap") if k in entry]
    if stray:
        # A combine-only key on a `file` or `self` entry does NOTHING, and an
        # `overlap` that does nothing reads exactly like a guard that is held.
        # That is the same silent-no-op class the absent-field refusal exists
        # for, one level out.
        fail("%s: declares %s without `files`, where %s no effect at all"
             % (where, " and ".join(repr(k) for k in stray),
                "they have" if len(stray) > 1 else "it has"))
        return None
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
    full = os.path.join(root, path)
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
    return measure_metric(root, os.path.dirname(path), spec, fail_stop)


def entry_number(record, entry, where, fail, root=None):
    """The number an entry stands for, `of` complement applied, or None.

    One reader for both callers on purpose: the gate compares this against the
    prose, and the builder renders it into the prose. If the two computed the
    complement separately they could come to disagree about a record, which is
    the defect the whole `counts` grammar exists against.
    """
    try:
        got = measured(record, entry, where, fail, root=root)
    except Stop:
        return None
    if got is None:
        return None
    if "of" in entry:
        if not isinstance(entry["of"], int):
            fail("%s: `of` must be an integer" % where)
            return None
        return entry["of"] - got
    return got


def tokens_in(text, where, field, fail):
    """Every (name, spec, start, end) a reader field writes, or None having failed.

    THE SPAN IS RETURNED so `resolve` can build its result from this same
    walk. An earlier draft validated here and then re-scanned with `re.sub`,
    which is two readings of one string that could come to disagree — this
    fleet's recurring defect at the scale of a function. It showed up as a
    KeyError rather than a refusal when the guards above were removed to test
    them: a crash is a failure a reader cannot act on.

    REFUSES A LEFTOVER BRACE. `{` with no `}`, a stray `}`, a name that is not
    an identifier, or a format spec outside the two allowed. Measured
    2026-09-29 across the shipped block, NO reader field contains a brace at
    all, so the delimiter needs no escape and an unmatched one is always a
    mistake rather than prose. If a record ever legitimately needs a literal
    brace, that is a decision to take then — with an escape stated in this
    docstring — and not a reason to let a malformed token through now.
    """
    out = []
    for m in TOKEN_RE.finditer(text):
        body = m.group(1)
        name, _, spec = body.partition(":")
        if not name.isidentifier():
            fail("%s: %s writes {%s}, whose name is not an identifier — a token "
                 "is {name} or {name:,} and nothing else" % (where, field, body))
            return None
        if spec not in SPECS:
            fail("%s: %s writes {%s}, and %r is not an allowed format — the "
                 "vocabulary is {name} and {name:,}, because a spec passed "
                 "through to format() accepts an unbounded mini-language in a "
                 "prose file" % (where, field, body, spec))
            return None
        out.append((name, spec, m.start(), m.end()))
    # Anything brace-shaped the token pattern did not consume is malformed.
    rest = TOKEN_RE.sub("", text)
    if "{" in rest or "}" in rest:
        fail("%s: %s carries an unmatched brace — a token is written {name} or "
             "{name:,}, and no reader field in this fleet uses a brace for "
             "anything else" % (where, field))
        return None
    return out


def resolve(text, values, where, field, fail):
    """The reader text with every token replaced by its measurement, or None.

    A TOKEN REFERENCING NO DECLARATION FAILS. That is the first of the three
    refusals the ruling names, and it is the vacuous-pass class turned on
    itself: rendering an unresolved `{chairs}` onto a card, or quietly dropping
    it, would both be worse than refusing to build.
    """
    found = tokens_in(text, where, field, fail)
    if found is None:
        return None
    missing = [n for n, _, _, _ in found if n not in values]
    if missing:
        fail("%s: %s writes %s, which %s declaration on this record — a token "
             "resolves from the record's own `counts`, so the question being "
             "asked stays visible"
             % (where, field,
                " and ".join("{%s}" % n for n in sorted(set(missing))),
                "name no" if len(set(missing)) > 1 else "names no"))
        return None
    out, at = [], 0
    for name, spec, start, end in found:
        out.append(text[at:start])
        out.append(SPECS[spec].format(values[name]))
        at = end
    out.append(text[at:])
    return "".join(out)


def record_values(record, where, fail, root=None):
    """{name: measurement} for the record's named declarations, or None.

    A name declared twice on one record FAILS rather than the later winning:
    which of two entries a token resolved through would be a rule nobody could
    see from the record.
    """
    values, seen = {}, set()
    ok = True
    for i, entry in enumerate(record.get("counts") or []):
        name = entry.get("name")
        if name is None:
            continue
        at = "%s counts[%d]" % (where, i)
        if not isinstance(name, str) or not name.isidentifier():
            fail("%s: `name` must be an identifier, not %r" % (at, name))
            ok = False
            continue
        if name in seen:
            fail("%s: declares the name %r a second time on this record — a "
                 "token could resolve through either" % (at, name))
            ok = False
            continue
        seen.add(name)
        got = entry_number(record, entry, at, fail, root=root)
        if got is None:
            ok = False
            continue
        values[name] = got
    return values if ok else None


def resolve_record(record, reader_fields, where, fail, root=None):
    """{field: resolved text} for a record's reader fields, or None having failed.

    THE SHIPPED TEXT IS WHAT EVERY READER-FIELD RULE MUST BE APPLIED TO, which
    is the third refusal in the ruling and Michigan's widening of it. READER_MAX
    on the authored text would refuse Michigan's own record: measured
    2026-09-29 its summary is 254 characters authored with three tokens against
    230 resolved, over the ceiling in the source file and under it on the card.
    So the very first record the form exists for could not be written down. The
    same argument covers the other three rules — a hostname, an ISO date and a
    shouting pair are all claims about what a READER is served — so the caller
    runs all four on what this returns.

    A record with no token is returned unchanged, which is why introducing this
    left all six instances' shipped files byte-identical.
    """
    values = record_values(record, where, fail, root=root)
    if values is None:
        return None
    out, ok = {}, True
    for key in reader_fields:
        text = record.get(key)
        if not isinstance(text, str):
            continue
        got = resolve(text, values, where, key, fail)
        if got is None:
            ok = False
            continue
        out[key] = got
    return out if ok else None
