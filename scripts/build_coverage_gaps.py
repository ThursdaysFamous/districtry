#!/usr/bin/env python3
"""
Emit data/app/coverage-gaps.json from the guidebook's GUIDEBOOK:BEGIN gaps block.

Why the guidebook is the source and not a hand-kept data file: every gap in it
already had to be recorded there with its rationale ("a deliberate 'we will not
ship this here' is recorded, never implied" — the guidebook's own maintenance
contract). Keeping the machine truth in the same document as the prose means a
gap cannot be closed in one place and left open in the other, and it follows the
coverage-map precedent that fleet_status.py already parses.

The app reads the emitted file to drive its Data gaps panel. `--check` is the CI
drift gate: it re-emits and compares, so editing the guidebook without
regenerating (or vice versa) fails the build rather than shipping a panel that
disagrees with the document of record.

TWO AUDIENCES, TWO SETS OF FIELDS. A gap record serves a maintainer (what was
measured, on what date, against which host, and why the obvious route is closed)
and a voter (what won't show up on my card, and why). Those are not the same
text, and for a year they were: the panel printed `blocker` verbatim, which runs
to ten thousand characters on the harder counties, so the one surface whose job
is to make absence legible was the least legible thing in the app.

So the fields are split by audience:
  - READER FIELDS — `summary`, `why`, `wanted` — are the only ones emitted. Each
    is capped at 240 characters and linted for the house style of the record
    (shouting, hostnames, ISO dates), because a cap is the only thing that keeps
    a research note from growing back into the panel one edit at a time.
  - THE RECORD — `blocker` — is required, unbounded, and NEVER shipped. It stays
    in the guidebook where the next maintainer looks, so nothing about the data
    journey is lost; it simply stops being read aloud to somebody who only wants
    to know who represents them.

Validation is deliberately strict about the things a reader would be misled by:
  - every entry needs a stable id, an area, a summary, a plain-language `why`, a
    measured blocker, and a `wanted` line, because a gap with no `wanted` invites
    re-sending a source that was already rejected;
  - `kind` must be one of no-source / blocked / data-quality — the two classes
    the panel is scoped to, plus `blocked` for a source that exists but refuses
    automation;
  - `layer` must name a real registered layer (or be null for a concept not yet
    built), so a gap can never point at a toggle that does not exist;
  - `counties` must name outline files that actually ship, since that is what
    makes the gap location-aware.

The guidebook lives in the CHICAGO repo only — it is a fleet document, and a
second copy in a sibling would be the drift trap docs/ENGINE_SYNC.md warns about.
So a sibling fork does NOT carry this script; its data/app/coverage-gaps.json is
generated from here with --metro/--out and lands in the fork through its engine
bump PR.

Usage:
    python3 scripts/build_coverage_gaps.py
    python3 scripts/build_coverage_gaps.py --check
    # emit a sibling fork's file from Chicago's guidebook:
    python3 scripts/build_coverage_gaps.py --metro nyc --out ny/data/app/coverage-gaps.json
"""

import argparse
import json
import os
import re
import sys
from scraper_common import make_fail  # noqa: E402  (shared machinery — do not fork)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUIDEBOOK = os.path.join(REPO_ROOT, "docs", "DATA_LAYER_GUIDEBOOK.md")
WORKSHEET = os.path.join(REPO_ROOT, "metro-worksheet.json")
OUT_PATH = os.path.join(REPO_ROOT, "il", "data", "app", "coverage-gaps.json")
APP_DATA_DIR = os.path.join(REPO_ROOT, "il", "data", "app")

GAPS_RE = re.compile(
    r"<!-- ==== GUIDEBOOK:BEGIN gaps ==== -->\s*```json\s*(.*?)\s*```",
    re.S,
)
KINDS = ("no-source", "blocked", "data-quality")
REQUIRED = ("id", "concept", "area", "kind", "summary", "why", "blocker", "wanted")
# Field order in the emitted file. Fixed so the output is byte-stable and --check
# compares content rather than dict ordering. `blocker` is deliberately absent:
# it is the maintainer's record, kept in the guidebook and never shipped.
FIELD_ORDER = ("id", "kind", "concept", "area", "layer", "counties",
               "summary", "why", "wanted")

# The three fields a voter reads, and the budget each gets. 240 characters is
# about two lines in the panel — enough for a plain sentence and not enough for
# a research note.
READER_FIELDS = ("summary", "why", "wanted")
READER_MAX = 240
# House-style tells that belong in `blocker` and read as noise on a card.
SHOUTING_RE = re.compile(r"\b[A-Z]{3,}\b[ ,]+\b[A-Z]{3,}\b")
HOSTNAME_RE = re.compile(r"\b[a-z0-9][a-z0-9-]*\.(?:gov|com|org|net|us|edu|io)\b")
ISO_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
URL_RE = re.compile(r"https?://")


fail = make_fail("build-coverage-gaps")


def load_gaps():
    with open(GUIDEBOOK, encoding="utf-8") as f:
        m = GAPS_RE.search(f.read())
    if not m:
        fail("no GUIDEBOOK:BEGIN gaps block in docs/DATA_LAYER_GUIDEBOOK.md")
    try:
        return json.loads(m.group(1))
    except ValueError as e:
        fail("gaps block is not valid JSON: %s" % e)


def worksheet():
    with open(WORKSHEET, encoding="utf-8") as f:
        return json.load(f)


def known_layer_ids(w):
    return {l["id"] for l in w["layers"]}


def shipped_outline_slugs(app_data_dir=None):
    d = app_data_dir or APP_DATA_DIR
    if not os.path.isdir(d):
        return None
    return {f[: -len("-county-outline.json")]
            for f in os.listdir(d) if f.endswith("-county-outline.json")}


def sibling_surfaces(out_path):
    """The layer ids and outline slugs of the instance an --out path points
    into, so a sibling's file is validated against ITS OWN app rather than
    against nothing.

    This is the hole that shipped a broken panel. Both per-fork checks used to
    be skipped whenever `--metro` named someone else, because the only
    worksheet and data dir this script knew were Illinois's. So Wisconsin's
    gaps were emitted for weeks with never a slug or layer id checked — and
    when all ten shipped with EMPTY counties, nothing said so. An instance
    laid out like this repo's own (`<root>/data/app/coverage-gaps.json`
    beside `<root>/metro-worksheet.json`) is now measured against itself; a
    path shaped like anything else falls back to skipping, exactly as before.
    """
    app_dir = os.path.dirname(os.path.abspath(out_path))
    inst = os.path.dirname(os.path.dirname(app_dir))
    ws = os.path.join(inst, "metro-worksheet.json")
    if not (os.path.basename(app_dir) == "app" and os.path.exists(ws)):
        return None, None
    with open(ws, encoding="utf-8") as f:
        sibling = json.load(f)
    return known_layer_ids(sibling), shipped_outline_slugs(app_dir)


def reader_problems(where, e):
    """Style problems in the three fields a voter actually reads.

    Every rule here has a counter-example in this file's own history: the panel
    once printed a 10,600-character blocker as its "Why" line, hostnames and
    HTTP status codes and ALL-CAPS findings included. None of that is wrong in
    the record; all of it is wrong on a card read by somebody who wants to know
    who represents them. Keep the finding, move it to `blocker`.
    """
    out = []
    for key in READER_FIELDS:
        text = str(e.get(key) or "").strip()
        if not text:
            continue                     # absence is REQUIRED's business
        if len(text) > READER_MAX:
            out.append("%s: %s is %d characters (max %d) — say it plainly here "
                       "and move the detail to `blocker`"
                       % (where, key, len(text), READER_MAX))
        if URL_RE.search(text) or HOSTNAME_RE.search(text):
            out.append("%s: %s names a hostname or URL — readers get the "
                       "publisher from the card, not from this line" % (where, key))
        if ISO_DATE_RE.search(text):
            out.append("%s: %s carries an ISO date — dates belong in `blocker`; "
                       "write \"since 2021\" if the timing matters to a reader"
                       % (where, key))
        if SHOUTING_RE.search(text):
            out.append("%s: %s shouts in capitals — that is record voice, not "
                       "reader voice" % (where, key))
    return out


def validate(entries, layer_ids, outlines):
    problems, seen = [], set()
    for i, e in enumerate(entries):
        where = e.get("id") or "entry %d" % i
        for key in REQUIRED:
            if not str(e.get(key) or "").strip():
                problems.append("%s: missing %s" % (where, key))
        problems.extend(reader_problems(where, e))
        if e.get("id") in seen:
            problems.append("%s: duplicate id" % where)
        seen.add(e.get("id"))
        if e.get("kind") not in KINDS:
            problems.append("%s: kind %r not one of %s" % (where, e.get("kind"), list(KINDS)))
        layer = e.get("layer")
        if layer_ids is not None and layer is not None and layer not in layer_ids:
            problems.append("%s: layer %r is not a registered layer id" % (where, layer))
        for slug in (e.get("counties") or []) if outlines is not None else []:
            if slug not in outlines:
                problems.append("%s: county %r has no data/app/%s-county-outline.json"
                                % (where, slug, slug))
        problems.extend(counted_prose_problems(where, e))
    return problems


# "In 12 of Wisconsin's 72 counties…" ABOVE A LIST OF ELEVEN. That shipped on
# 2026-09-02 and every gate stayed green, because the gates compare the shipped
# JSON to the guidebook and the two agreed — on a number that was wrong in both.
# A COUNT IN PROSE IS A CLAIM ABOUT THE ARRAY BESIDE IT, and it is the one thing
# an equality check between two copies can never see. The cause was a
# multi-replacement edit whose last assertion failed, so none of the earlier
# replacements were written and nobody re-read the file; the count then went
# stale silently for one release. This makes the prose answer to the data.
# A gap record that states how many counties it covers must state the number it
# LISTS. Three shapes appear in practice and all three are checked, because the
# first pattern here caught only one of them: "In 12 of ..." (the original),
# "... 67 of the 91 this site serves" (a summary written for a reader), and an
# `area` of "67 served counties". The second and third went unchecked, which
# matters most exactly when it is easiest to get wrong — two changes in flight
# each removing one county from the same list, each correctly decrementing the
# count to the same value, and the merge of the two leaving the list one shorter
# than the number above it. The gate turns that silent wrong answer into a
# failed build. `ward-polling-places` deliberately does not match: its area
# counts WARDS and municipalities, not counties.
COUNTED_PROSE = re.compile(r"(?i)\bIn (\d+) of\b|\b(\d+) of the \d+\b"
                           r"|^(\d+) served counties$")


def counted_prose_problems(where, entry):
    """A gap whose summary counts counties must count the ones it lists."""
    counties = entry.get("counties") or []
    if not counties:
        return []                        # a gap with no county list counts nothing
    out = []
    for field in ("summary", "area"):
        said = COUNTED_PROSE.search(str(entry.get(field) or ""))
        if not said:
            continue
        n = int(next(g for g in said.groups() if g))
        if n != len(counties):
            out.append("%s: the %s says %d counties and `counties` lists %d — the "
                       "panel would print a number above a list that contradicts it"
                       % (where, field, n, len(counties)))
    return out


def render(entries):
    out = []
    for e in entries:
        row = {}
        for key in FIELD_ORDER:
            if key == "counties":
                row[key] = list(e.get("counties") or [])
            elif key == "layer":
                row[key] = e.get("layer") or None
            else:
                row[key] = e[key]
        out.append(row)
    # id order, so a reordered guidebook block does not churn the data file
    out.sort(key=lambda r: r["id"])
    # Keyed BY GAP ID, not wrapped in a list: validate_index.py's roster check
    # measures len() of the top-level object, so a {"gaps": [...]} wrapper would
    # give it a floor of 1 and guard nothing. Keyed, the floor is a real count —
    # and it matches the other keyed payloads (il-county-clerks, municipal-officials).
    return json.dumps({r["id"]: r for r in out}, separators=(",", ":"), ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify the shipped file, write nothing")
    ap.add_argument("--metro", help="emit another fork's key instead of this worksheet's")
    ap.add_argument("--out", help="write somewhere other than this repo's data/app/")
    args = ap.parse_args()
    out_path = args.out or OUT_PATH

    # The guidebook is a fleet-wide document with one array per metro (the
    # coverage-map block's shape), so the fork reads ITS OWN key rather than a
    # hardcoded one — that is what lets the same script run in every fork.
    w = worksheet()
    metro = args.metro or w["this_metro"]

    # --metro AND --out ARE ONE ARGUMENT, and forgetting the second one is the
    # only way this script has ever touched a wrong file. --metro chooses the
    # guidebook BLOCK; --out chooses the FILE, and nothing tied them together.
    # `--metro wisconsin` alone read Wisconsin's gaps and wrote them over
    # ILLINOIS's shipped file, reporting success. Nothing downstream named the
    # cause: build_county_status.py failed on "gap 'aldermanic-incomplete-
    # filings' names unknown county slug 'calumet'" and build_history_page.py
    # on a stale page, both symptoms one step removed — and the pair only fired
    # at all because the two states' slug vocabularies happen to disagree. Two
    # metros that shared a slug would have shipped it.
    #
    # THE --check PATH WAS THE WORSE HALF AND IS WHY THIS GUARD COVERS IT.
    # `--check --metro wisconsin` compares Wisconsin's block against Illinois's
    # FILE, so it reports FAIL on a correct tree — and reports **OK** on a tree
    # where the bad write above has already happened, because then the wrong
    # file really does hold the wrong content. A verification that passes
    # BECAUSE of the defect it should catch is worse than one that writes it,
    # and this one did exactly that on 2026-09-02 before Lincoln shipped. CI
    # always pairs the two flags (smoke-test.yml); it is the hand-run that lies.
    if args.metro and not args.out and metro != w["this_metro"]:
        fail("--metro %s needs --out: --metro picks the guidebook block and --out "
             "picks the file, so without it this %s %s's gaps against %s — this "
             "repo's own %s file. Pass the sibling's path, e.g. --metro %s --out "
             "<tag>/data/app/coverage-gaps.json."
             % (metro, "checks" if args.check else "writes", metro,
                os.path.relpath(OUT_PATH, REPO_ROOT), w["this_metro"], metro))
    gaps = load_gaps()
    entries = gaps.get(metro)
    if entries is None:
        fail("gaps block has no %r array (keys: %s). Add one for this fork, even if "
             "empty, so the absence is deliberate rather than an oversight."
             % (metro, list(gaps)))

    # Layer ids and outline slugs are per-fork. This repo's own metro measures
    # against this repo; a sibling measures against the instance its --out path
    # points into (sibling_surfaces), and only an unrecognizable path skips.
    own = metro == w["this_metro"]
    if own:
        layer_ids, outlines = known_layer_ids(w), shipped_outline_slugs()
    else:
        layer_ids, outlines = sibling_surfaces(out_path)
    problems = validate(entries, layer_ids, outlines)

    # LOCATION AWARENESS IS THE PANEL'S WHOLE POINT, so an instance that ships
    # county outlines and tags no gap with one has a dead "Where you clicked"
    # section and does not know it. That is not hypothetical: Wisconsin shipped
    # exactly that state — ten gaps, every `counties` array empty — and the
    # panel told a reader who had clicked to click. Every other guard passed.
    mappable = sum(1 for e in entries if (e.get("counties") or []))
    if outlines and entries and not mappable:
        problems.append(
            "%s ships %d county outline(s) and not one of its %d gaps names a "
            "county, so the panel can never lead with the gaps that apply where "
            "a reader clicked. Tag the gaps whose area maps to counties."
            % (metro, len(outlines), len(entries)))
    if problems:
        for p in problems:
            print("  %s" % p, file=sys.stderr)
        fail("%d invalid gap entr%s" % (len(problems), "y" if len(problems) == 1 else "ies"))

    payload = render(entries)
    by_kind = {}
    for e in entries:
        by_kind[e["kind"]] = by_kind.get(e["kind"], 0) + 1
    summary = ", ".join("%s %d" % (k, by_kind[k]) for k in sorted(by_kind))

    if args.check:
        if not os.path.exists(out_path):
            fail("data/app/coverage-gaps.json is missing — run this script")
        with open(out_path, encoding="utf-8") as f:
            shipped = f.read()
        if shipped != payload:
            fail("data/app/coverage-gaps.json differs from the guidebook's gaps block "
                 "(%d vs %d bytes). Edit the guidebook, then regenerate."
                 % (len(shipped), len(payload)))
        print("build-coverage-gaps: OK — shipped file matches the guidebook "
              "(%s: %d gaps, %s; %d mapped to counties)"
              % (metro, len(entries), summary, mappable))
        return

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(payload)
    print("build-coverage-gaps: wrote %s — %s: %d gaps (%s), %d mapped to "
          "counties, %d bytes"
          % (os.path.relpath(out_path, REPO_ROOT), metro, len(entries), summary,
             mappable, len(payload)))


if __name__ == "__main__":
    main()
