#!/usr/bin/env python3
"""
How much of each county page is its own text, and how much is repeated.

WHY THIS EXISTS. The SEO audit of 15 September 2026 reported the county pages
at a median 27% unique text against a 60% target, with 2 of 170 passing, and
the fix it proposed — collapse the repeated provenance, add per-county facts —
is only checkable against a number. The number was produced once, by hand, in a
scratch directory. A measurement filed nowhere is one the next pass repeats.

TWO NUMBERS, BECAUSE ONE OF THEM MISSES THE DEFECT THE OTHER FINDS.

  UNIQUE  the share of a page's distinct 5-word shingles that appear on no
          other county page in the fleet. This is the audit's own measure and
          it answers "is this page substantially the same document as its 182
          siblings".

  REPEAT  the share of a page's words that are inside a sentence the page
          itself says more than once. The shingle measure CANNOT see this,
          because it compares SETS: a sentence printed 29 times contributes
          exactly as much as a sentence printed once. Measured 2026-09-15,
          Wisconsin's Dunn County page said the same 27-word provenance
          sentence 29 times — 783 of its 1,312 words, 60% of the page — and
          scored an unremarkable 47% unique. Seven pages did it, 134
          repetitions between them. Lifting that sentence to one copy per page
          took Dunn from 1,312 words to 556 and moved the shingle figure by
          nothing at all.

IT REPORTS AND DOES NOT GATE. The target is 60% and the fleet is not there:
a five-member Iowa board has little text to be unique WITH, and inventing some
to clear a threshold is the opposite of what these pages are for. The figure is
printed so a change can be measured against it, and the worst pages are named
so the next lever is obvious rather than guessed at.

    python3 scripts/measure_county_page_text.py
    python3 scripts/measure_county_page_text.py --worst 20
"""

import argparse
import collections
import glob
import html
import os
import re
import statistics
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHINGLE = 5
TARGET = 0.60


def page_text(path):
    with open(path, encoding="utf-8") as f:
        src = f.read()
    m = re.search(r"<main.*?</main>", src, re.S)
    if not m:
        return None
    text = html.unescape(re.sub(r"<[^>]+>", " ", m.group(0)))
    return re.sub(r"\s+", " ", text).strip()


def words(text):
    return re.sub(r"[^a-z0-9 ]", " ", text.lower()).split()


def repeat_share(text):
    """The share of a page's words inside a sentence it prints more than once."""
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text)]
    sents = [s for s in sents if len(s.split()) >= 5]
    if not sents:
        return 0.0
    counts = collections.Counter(sents)
    total = sum(len(s.split()) for s in sents)
    dupe = sum(len(s.split()) * (n - 1) for s, n in counts.items() if n > 1)
    return dupe / total if total else 0.0


def pages():
    out = {}
    for pattern in ("*/county-board/*.html", "*/county-supervisor/*.html",
                    "*/county-commissioner/*.html"):
        for path in sorted(glob.glob(os.path.join(REPO_ROOT, pattern))):
            text = page_text(path)
            if text:
                out[os.path.relpath(path, REPO_ROOT)] = text
    return out


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--worst", type=int, default=8,
                    help="how many of the least distinctive pages to name")
    args = ap.parse_args()

    corpus = pages()
    if not corpus:
        print("measure-county-page-text: FAIL — no county pages found. Run "
              "`python3 scripts/build_county_pages.py` first.", file=sys.stderr)
        return 1

    grams, doc_freq = {}, collections.Counter()
    for rel, text in corpus.items():
        w = words(text)
        g = {tuple(w[i:i + SHINGLE]) for i in range(max(0, len(w) - SHINGLE + 1))}
        grams[rel] = g
        for x in g:
            doc_freq[x] += 1

    rows = []
    for rel, g in grams.items():
        if not g:
            continue
        uniq = sum(1 for x in g if doc_freq[x] == 1) / len(g)
        rows.append((uniq, repeat_share(corpus[rel]), len(words(corpus[rel])), rel))
    rows.sort()

    passing = sum(1 for r in rows if r[0] >= TARGET)
    repeating = [r for r in rows if r[1] > 0.05]
    print("measure-county-page-text: %d page(s)" % len(rows))
    print("  unique text   median %4.1f%%   mean %4.1f%%   %d of %d at or above %d%%"
          % (100 * statistics.median(r[0] for r in rows),
             100 * statistics.mean(r[0] for r in rows), passing, len(rows),
             100 * TARGET))
    print("  repeated text %d page(s) repeat a sentence over 5%% of their words%s"
          % (len(repeating),
             "" if not repeating else
             ", worst %.0f%% (%s)" % (100 * max(r[1] for r in repeating),
                                      max(repeating, key=lambda r: r[1])[3])))
    print("  length        median %d words, %d page(s) under 300"
          % (statistics.median(r[2] for r in rows),
             sum(1 for r in rows if r[2] < 300)))
    print("  least distinctive:")
    for uniq, rep, n, rel in rows[:args.worst]:
        print("    %5.1f%% unique  %5.1f%% repeated  %5d words  %s"
              % (100 * uniq, 100 * rep, n, rel))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        # Piped into `head`, which closed stdout. Python's default is a
        # traceback, which on a reporting script reads as a failure.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(0)
