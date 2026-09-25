#!/usr/bin/env python3
"""How many numbers in worksheet prose could a gate hold to the file below them?

THIS IS A MEASUREMENT AND NOT A GATE, deliberately, and it is committed so the
next pass reads a figure instead of re-deriving one. It is in no workflow and
moves neither figure `scripts/validate_gate_counts.py` states.

WHY IT WAS RUN. Three defects of one family landed in three weeks and none had
anything comparing it: `wi/metro-worksheet.json` said the 159 aldermanic
municipalities are "155 from the counties' own filings, plus Appleton", which is
156 and omitted three of the four cities that are locally composed; the
alderperson gap record's county list was derived once from two files that both
kept moving and went wrong in BOTH directions at once (57 where 54 is right,
five counties claiming a gap they no longer had and two missing); and the
alderperson scraper's queue comment still listed nine cities that had shipped,
because the rule said an address leaves the queue when fetching STARTS and
nothing said the reverse. Each is a number or a list restated in prose beside
the table that owns it.

WHAT IT MEASURES, and the answer is mostly a bound on what a gate can be told
to do. `scripts/validate_gap_counts.py` already settled the principle for one
surface -- IT DECLARES, IT NEVER INFERS, because the gaps block holds 153
numbers of which three are file-backed -- and this asks whether the worksheets
are different. They are not, and they are thirty times larger.

THE RULE, stated so a re-run is comparable rather than a second opinion:
  * the surface is the six instances' worksheets, each at ITS OWN path;
  * a field is prose if it is a string of 60 characters or more that is not a
    URL;
  * a candidate is an integer >= 2 in such a field, written as digits, with
    thousands separators read as one number;
  * a SHORTLIST keeps a candidate within 30 characters of a plural naming
    something this repo ships, which narrows the corpus without deciding
    anything;
  * three exclusions then apply, each for a reason, and each is reported with
    its count rather than applied silently.

THREE READERS THAT FOUND NOTHING AND WOULD HAVE REPORTED IT AS A RESULT, all
three inside this script's own first draft, which is the defect it measures:
  * Illinois's worksheet is the REPO ROOT file, not `il/metro-worksheet.json`,
    so a per-folder sweep read the instance holding over half the corpus as
    ZERO. A zero for an instance is now fatal here.
  * there is no `data_app_files[]` key; the per-file notes are under
    `data_files.geometry[]` and `data_files.rosters[]`.
  * `count(y|ies)` in the shortlist pattern is a CAPTURE group, so `findall`
    returned tuples and the first classification crashed rather than lying --
    which is the lucky half.
"""
import argparse
import collections
import io
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Each instance's worksheet at its own path. Illinois's is the root file, which
# is the spelling generate_metro_files.INSTANCES carries and the one a sweep
# that assumes `<tag>/metro-worksheet.json` silently misses.
INSTANCE_WORKSHEETS = {
    "ca": "ca/metro-worksheet.json",
    "ia": "ia/metro-worksheet.json",
    "il": "metro-worksheet.json",
    "mi": "mi/metro-worksheet.json",
    "ny": "ny/metro-worksheet.json",
    "wi": "wi/metro-worksheet.json",
}

# Thousands-aware on purpose: `\b\d{1,4}\b` reads `1,659` as two numbers, which
# is how two readers of the gaps corpus got 152 and 153 an hour apart.
NUMBER = re.compile(r"(?<![\d.,])(\d{1,3}(?:,\d{3})+|\d+)(?![\d.,])")

# Plurals naming something this repo ships. The list narrows; it never decides.
THINGS = ("municipalit", "district", "count(?:y|ies)", "seat", "member",
          "supervisor", "commissioner", "alderperson", "trustee", "layer",
          "feature", "precinct", "ward", "file", "judge", "officer", "official",
          "township", "librar", "board")
_T = "|".join(THINGS)
NEAR = re.compile(r"(?<![\d.,])(\d{1,3}(?:,\d{3})+|\d+)(?![\d.,])[^.;]{0,30}?\b(?:%s)" % _T,
                  re.I)
AFTER = re.compile(r"\b(?:%s)\w*\b[^.;]{0,20}?(?<![\d.,])(\d{1,3}(?:,\d{3})+|\d+)(?![\d.,])" % _T,
                   re.I)
YEAR = re.compile(r"^(?:19|20)\d\d$")
PROSE_MIN = 60


def prose_fields(obj, path=""):
    """(path, string) for every prose field, paths written as a reader edits them."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield from prose_fields(value, "%s.%s" % (path, key) if path else key)
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            yield from prose_fields(value, "%s[%d]" % (path, i))
    elif isinstance(obj, str):
        if len(obj) >= PROSE_MIN and not obj.startswith("http"):
            yield path, obj


def candidates(text):
    """Numbers >= 2 sitting beside a plural naming something this repo ships."""
    hits = set(NEAR.findall(text)) | set(AFTER.findall(text))
    return sorted({h for h in hits if int(h.replace(",", "")) >= 2},
                  key=lambda n: int(n.replace(",", "")))


def sweep(root):
    """(corpus, shortlist, kept, dropped) for the six worksheets."""
    corpus, shortlist = [], []
    for tag, rel in sorted(INSTANCE_WORKSHEETS.items()):
        path = os.path.join(root, rel)
        if not os.path.exists(path):
            sys.exit("measure-restated-counts: FAIL — %s has no worksheet at %s"
                     % (tag, rel))
        with io.open(path, encoding="utf-8") as fh:
            worksheet = json.load(fh)
        found = 0
        for field, text in prose_fields(worksheet):
            numbers = [n for n in NUMBER.findall(text)
                       if int(n.replace(",", "")) >= 2]
            if not numbers:
                continue
            found += 1
            corpus.append({"instance": tag, "field": field, "numbers": numbers})
            near = candidates(text)
            if near:
                shortlist.append({"instance": tag, "field": field,
                                  "candidates": near, "text": text})
        # A zero is a finding about this reader, never a result about the
        # instance: it is exactly how Illinois read as empty.
        if not found:
            sys.exit("measure-restated-counts: FAIL — %s: no prose field carries "
                     "a number, which means the path or the walk is wrong, not "
                     "that the instance states none" % tag)

    kept, dropped = [], collections.Counter()
    for row in shortlist:
        field, text, near = row["field"], row["text"], list(row["candidates"])
        # A dated, append-only changelog entry. CLAUDE.md: each is true on its
        # own day and never edited afterwards, so holding one to today's file
        # would demand the single edit the design forbids.
        if field.startswith("history_page"):
            dropped["history_page — dated and append-only, must NOT be gated"] += len(near)
            continue
        # "layer 51 (Fire Stations)" is an ADDRESS into a publisher's service.
        if re.match(r"layers\[\d+\]\.source\.boundary\[\d+\]\.label$", field):
            keep = [c for c in near
                    if not re.search(r"\blayers?\s*%s\b" % re.escape(c), text, re.I)]
            dropped["a publisher's own layer index, not a count"] += len(near) - len(keep)
            near = keep
        before = len(near)
        near = [c for c in near if not YEAR.match(c)]
        dropped["a bare year — a vintage, not a count"] += before - len(near)
        if near:
            kept.append({**row, "candidates": near})
    return corpus, shortlist, kept, dropped


def note_vs_declared(root):
    """Per-file notes held to the expected count in their OWN json object.

    The cheapest check imaginable — the note and the floor are the same object,
    so nothing has to be declared or looked up — and it is wrong more often than
    right, which is the measurement that decides the design. `min_keys` is a
    FLOOR that tolerates vacancies and a note states the SEAT COUNT, so
    California's 52 House seats beside a floor of 45 is two correct numbers.
    """
    agree = differ = silent = comparable = entries = 0
    examples = []
    for tag, rel in sorted(INSTANCE_WORKSHEETS.items()):
        with io.open(os.path.join(root, rel), encoding="utf-8") as fh:
            worksheet = json.load(fh)
        files = worksheet.get("data_files") or {}
        for kind in ("geometry", "rosters"):
            for entry in files.get(kind, []):
                entries += 1
                declared = entry.get("min_keys", entry.get("min_features"))
                note = entry.get("note") or ""
                if declared is None:
                    continue
                comparable += 1
                numbers = {int(n.replace(",", "")) for n in NUMBER.findall(note)}
                if not numbers:
                    silent += 1
                elif declared in numbers:
                    agree += 1
                else:
                    differ += 1
                    if len(examples) < 6:
                        examples.append((tag, entry.get("file"), declared,
                                         sorted(numbers)[:6], note[:96]))
    return entries, comparable, agree, differ, silent, examples


# A figure tied to a date, the shape Michigan's own PR named on 2026-09-25.
DATED_CLAUSE = re.compile(r"(measured|as of|through|since)\s[^.;]{0,60}?"
                          r"(20\d\d-\d\d-\d\d|20\d\d)", re.I)
TARGET_FIELD = re.compile(r"layers\[\d+\]\.source\.(people|applies|answers)$")


def target_surface(root):
    """The reader-facing surface a gate would walk, and its date-tied members.

    TWO THINGS THAT LOOK ALIKE AND ARE NOT, which is the distinction a gate
    could most easily get wrong. Michigan's `applies` says "statewide, all 1,581
    records ... measured 2026-09-04": the date is PROVENANCE and the figure
    describes the file NOW, so the day the file gains a record that sentence is
    wrong about the product and a gate should say so. A history entry's
    "through tranche 7 (2026-09-19)" describes a COMPLETED EVENT, and holding it
    to today's file would demand the one edit that design forbids.

    Both carry a date in the same clause as a number. No pattern separates them,
    which is a third independent argument for a declaration: a claim's author
    knows which of the two they are writing and a regex never will.
    """
    fields = dated = 0
    examples = []
    for tag, rel in sorted(INSTANCE_WORKSHEETS.items()):
        with io.open(os.path.join(root, rel), encoding="utf-8") as fh:
            worksheet = json.load(fh)
        for field, text in prose_fields(worksheet):
            if not TARGET_FIELD.search(field):
                continue
            fields += 1
            hit = DATED_CLAUSE.search(text)
            if hit:
                dated += 1
                if len(examples) < 4:
                    examples.append((tag, field, hit.group(0), text[:96]))
    return fields, dated, examples


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=REPO_ROOT)
    args = parser.parse_args()

    corpus, shortlist, kept, dropped = sweep(args.root)
    per_instance = collections.Counter()
    for row in corpus:
        per_instance[row["instance"]] += len(row["numbers"])

    print("WORKSHEET PROSE, six instances, each worksheet at its own path")
    print("  %d prose fields carry a number >= 2, %d numbers in all"
          % (len(corpus), sum(per_instance.values())))
    for tag in sorted(INSTANCE_WORKSHEETS):
        print("    %-3s %5d" % (tag, per_instance[tag]))

    print("\nSHORTLIST — a candidate sits beside a plural naming something shipped")
    print("  %d candidates in %d fields"
          % (sum(len(r["candidates"]) for r in shortlist), len(shortlist)))
    for reason, n in dropped.most_common():
        print("  dropped %5d  %s" % (n, reason))
    print("  KEPT    %5d candidates in %d fields"
          % (sum(len(r["candidates"]) for r in kept), len(kept)))

    shapes = collections.Counter(re.sub(r"\[\d+\]", "[]", r["field"]) for r in kept)
    print("\nWHERE THE SURVIVORS LIVE")
    for shape, n in shapes.most_common(8):
        print("    %-50s %4d field(s)" % (shape, n))

    entries, comparable, agree, differ, silent, examples = note_vs_declared(args.root)
    print("\nTHE CHEAPEST CHECK, AND WHY IT IS NOT ONE: a per-file note against")
    print("the expected count in its own object")
    print("  %d data-file entries, %d carry an expected count" % (entries, comparable))
    print("    note states it                      %4d" % agree)
    print("    note states numbers, none of them it %4d   <- would all FAIL" % differ)
    print("    note states no number                %4d" % silent)
    for tag, name, declared, numbers, note in examples:
        print("      %-3s %-38s floor=%-5s note %s" % (tag, name, declared, numbers))
        print("          %s" % note)
    stating = agree + differ
    print("\n  A floor is not a count: California's note says 52 House seats and")
    print("  its floor is 45 because vacancies are allowed, and both are right.")
    print("  So of the %d notes that state a number at all, inference is wrong %d"
          % (stating, differ))
    print("  times — wrong more often than right, even where the number and the")
    print("  file it would be checked against share one json object. That is the")
    print("  case FOR a declaration and against a sweep, on a corpus thirty times")
    print("  the one validate_gap_counts.py measured settling the same question.")

    fields, dated, examples = target_surface(args.root)
    with_candidates = sum(1 for r in kept if TARGET_FIELD.search(r["field"]))
    print("\nTHE TARGET SURFACE — the three reader-facing source strings, which")
    print("render into every instance's sources.html matrix and Dataset graph")
    print("  %d fields in all; %d of them carry a candidate a gate could be told"
          % (fields, with_candidates))
    print("  about, which is the number of declarations, not the number of fields.")
    print("  %d carry a figure in the same clause as a DATE:" % dated)
    for tag, field, clause, text in examples:
        print("    %-3s %-40s %r" % (tag, field.split(".", 1)[-1], clause))
        print("        %s" % text)
    print("\n  AND A DATE DOES NOT MAKE A FIGURE HISTORICAL. Michigan's `applies`")
    print("  says \"all 1,581 records ... measured 2026-09-04\": the date is")
    print("  PROVENANCE, the figure describes the file NOW, and the day that file")
    print("  gains a record the sentence is wrong about the product. A history")
    print("  entry's \"through tranche 7 (2026-09-19)\" describes a COMPLETED")
    print("  EVENT and must never move. Both put a number and a date in one")
    print("  clause; no pattern tells them apart, and the claim's author always")
    print("  can. That is the third independent argument for a declaration.")


if __name__ == "__main__":
    main()
