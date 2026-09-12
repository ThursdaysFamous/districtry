#!/usr/bin/env python3
"""
Splice the shared engine into every instance's app files
(docs/DEV_PROCESS_ASSESSMENT.md, stage R3).

WHY THIS EXISTS. The fleet used to keep its metro-agnostic engine byte-identical
across separate REPOS by publishing it as a hash-pinned release and splicing it
in at deploy time. That machinery is retired (R2.1) and the forks are moving
into this repo as folders, so the question stops being "how do we keep N copies
in step" and becomes "why is there more than one copy". There is now ONE copy of
each engine block, under engine/, and each instance's index.html and sw.js are
composed from it. Parity stops being something a checker asserts and becomes
something the layout makes true.

WHAT IS SHARED AND WHAT IS NOT. Only the ENGINE fences. Everything outside them
is instance-owned and lives in the instance's own file: its layer modules, its
METRO config, its GENERATED regions, its TEMPLATE span markers. That division is
deliberate and it is why this script is small — an earlier draft also split the
instance-local text into fragment files, which duplicated ~26,000 lines per
instance for no guarantee this does not already give, and put the composer in a
fight with generate_metro_files.py over who writes a GENERATED region. The
generator owns those regions in the composed file; this script never touches a
byte outside an ENGINE fence.

THE CONTRACT IS BYTE-IDENTITY. `--check` recomposes in memory and diffs; any
difference is a hard failure. The composed app files stay COMMITTED — they are
what `python3 -m http.server` serves, what the smoke test drives, what Pages
publishes, and what a person can open and read end to end. This script is a
drift gate over a representation that already exists, exactly like
generate_metro_files.py, and never becomes load-bearing at runtime.

ORDER OF OPERATIONS when both run: generate_metro_files.py first (it writes
GENERATED regions, all of which are outside ENGINE fences), then this. They
cannot contend for a line.

Modes:
    python3 scripts/compose_app.py --extract-from il   # populate engine/ from one instance
    python3 scripts/compose_app.py                     # splice engine/ into every instance
    python3 scripts/compose_app.py --check             # verify; exit 1 on any drift

--extract-from is the adoption door, run once when engine/ is created (or when a
block is deliberately added). Afterwards engine/ is the source: edit the block
there and recompose. Editing an ENGINE fence inside an instance file is the one
thing this design asks you not to do, and --check is what notices.
"""

import argparse
import difflib
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE_DIR = os.path.join(REPO_ROOT, "engine")

# Instance id -> its app files, relative to the repo root. A new instance is one
# row here; nothing else in this script knows how many instances exist.
INSTANCES = {
    "il": ["il/index.html", "il/sw.js"],
    "ca": ["ca/index.html", "ca/sw.js"],
    "ny": ["ny/index.html", "ny/sw.js"],
    "wi": ["wi/index.html", "wi/sw.js"],
    "ia": ["ia/index.html", "ia/sw.js"],
    "mi": ["mi/index.html", "mi/sw.js"],
}

# The sub-pages — every published page that is not the app. They compose the
# same way the apps do, and they were added here because the alternative had
# already been tried by accident: thirteen hand-kept copies of one stylesheet,
# which diverged into four variants, of which three were wrong. `root` is a
# pseudo-instance for the pages that sit at the repo root rather than inside an
# instance folder.
SUBPAGES = {
    # sponsorship.html was outside this list while carrying the same footer
    # byline as the twenty pages in it — found on 2026-09-12 when the byline
    # became one shared block and one page would have kept its own copy.
    "root": ["privacy.html", "sponsorship.html", "traffic.html"],
    "il": ["il/faq.html", "il/sources.html", "il/police-district.html",
           "il/school-board.html", "il/county-board.html", "il/ward.html",
           "il/precinct.html"],
    "ny": ["ny/faq.html", "ny/sources.html", "ny/council-district.html",
           "ny/community-board.html"],
    "ca": ["ca/faq.html", "ca/sources.html", "ca/supervisor-district.html"],
    "wi": ["wi/faq.html", "wi/sources.html", "wi/county-board.html"],
    "ia": ["ia/faq.html", "ia/sources.html", "ia/county-supervisor.html"],
    "mi": ["mi/faq.html", "mi/sources.html", "mi/county-commissioner.html"],
}

# Blocks whose ONE source is engine/shared/<name>.txt rather than
# engine/<filename>/<name>.txt. A block belongs here when more than one FILENAME
# carries it: the sub-page shell is spliced into eight distinct basenames, and
# keying it by filename would put eight copies back where this file just removed
# thirteen. Resolution stays deterministic — a shared name never also resolves
# per-filename.
SHARED_BLOCKS = {"styles-subpage", "tokens-brand", "footer-byline",
                 "footer-independence"}

ENGINE_RE = re.compile(
    r"^[ \t]*(?:/\*|<!--|#|//)?[ \t]*==== ENGINE:(BEGIN|END) "
    r"([a-z0-9][a-z0-9-]*) ====[ \t]*(?:\*/|-->)?[ \t]*$"
)
OTHER_MARKER_RE = re.compile(
    r"^[ \t]*(?:/\*|<!--|#|//)?[ \t]*==== (GENERATED|TEMPLATE|METRO):(BEGIN|END) "
    r"([a-z0-9][a-z0-9-]*) ====[ \t]*(?:\*/|-->)?[ \t]*$"
)


def fail(msg):
    print("compose-app: FAIL — " + msg, file=sys.stderr)
    sys.exit(1)


def read(path):
    with open(path, encoding="utf-8", newline="") as f:
        text = f.read()
    if "\r" in text:
        fail("%s has CR/CRLF line endings; this repo is LF-only" % path)
    return text


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def scan(text, label):
    """Ordered [(name, interior_text, begin_line, end_line)] for every ENGINE
    fence, where interior EXCLUDES the two marker lines.

    Splicing replaces interiors only, so the markers — and every byte outside
    them — are the instance's own and survive untouched.
    """
    lines = text.splitlines(keepends=True)
    found = []
    i = 0
    while i < len(lines):
        m = ENGINE_RE.match(lines[i].rstrip("\n"))
        if not m:
            i += 1
            continue
        kind, name = m.groups()
        if kind != "BEGIN":
            fail("%s:%d: stray ENGINE:END %s" % (label, i + 1, name))
        start = i
        i += 1
        closed = None
        while i < len(lines):
            bare = lines[i].rstrip("\n")
            inner = ENGINE_RE.match(bare)
            if inner and inner.group(1) == "BEGIN":
                fail("%s:%d: ENGINE fence %r nested inside %r"
                     % (label, i + 1, inner.group(2), name))
            om = OTHER_MARKER_RE.match(bare)
            if om:
                fail("%s:%d: %s marker inside ENGINE fence %r"
                     % (label, i + 1, om.group(1), name))
            if inner and inner.group(1) == "END":
                if inner.group(2) != name:
                    fail("%s:%d: ENGINE:END %s closes fence %r"
                         % (label, i + 1, inner.group(2), name))
                closed = i
                break
            i += 1
        if closed is None:
            fail("%s: ENGINE fence %r is never closed" % (label, name))
        found.append((name, "".join(lines[start + 1:closed]), start, closed))
        i = closed + 1
    seen = set()
    for name, _, _, _ in found:
        if name in seen:
            fail("%s: duplicate ENGINE fence %r" % (label, name))
        seen.add(name)
    return found, lines


def block_path(fname, name):
    if name in SHARED_BLOCKS:
        return os.path.join(ENGINE_DIR, "shared", name + ".txt")
    return os.path.join(ENGINE_DIR, fname, name + ".txt")


def targets(ids):
    """[(instance, relative path)] for every file the given ids own — apps first,
    then sub-pages. `root` owns sub-pages only, which is why it is not in
    INSTANCES."""
    out = []
    for i in ids:
        for rel in INSTANCES.get(i, []):
            out.append((i, rel))
        for rel in SUBPAGES.get(i, []):
            out.append((i, rel))
    return out


def splice(text, label):
    """Return `text` with every ENGINE interior replaced by the shared copy."""
    fences, lines = scan(text, label)
    fname = os.path.basename(label)
    out = []
    prev = 0
    for name, _interior, start, end in fences:
        p = block_path(fname, name)
        if not os.path.exists(p):
            fail("%s: ENGINE block %r has no shared source at %s — run "
                 "--extract-from on the reference instance, or the block is new "
                 "and needs adding there deliberately"
                 % (label, name, os.path.relpath(p, REPO_ROOT)))
        out.append("".join(lines[prev:start + 1]))   # up to and incl. BEGIN marker
        out.append(read(p))                          # the shared interior
        prev = end                                   # END marker starts the next run
    out.append("".join(lines[prev:]))
    return "".join(out)


def do_extract(instance):
    if instance not in INSTANCES and instance not in SUBPAGES:
        fail("unknown instance %r" % instance)
    total = 0
    for _i, rel in targets([instance]):
        text = read(os.path.join(REPO_ROOT, rel))
        fences, _ = scan(text, rel)
        fname = os.path.basename(rel)
        for name, interior, _, _ in fences:
            write(block_path(fname, name), interior)
        total += len(fences)
        print("compose-app: %s — extracted %d engine block(s) to engine/%s/"
              % (rel, len(fences), fname))
    print("compose-app: engine/ now holds %d block(s), extracted from %r"
          % (total, instance))


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--instance", action="append", metavar="ID",
                    help="limit to one instance (repeatable; default: all)")
    ap.add_argument("--check", action="store_true",
                    help="verify each instance matches the shared engine; exit 1 on drift")
    ap.add_argument("--extract-from", metavar="ID",
                    help="populate engine/ FROM this instance (the adoption door)")
    args = ap.parse_args()

    if args.extract_from:
        if args.check:
            fail("--extract-from and --check are mutually exclusive")
        do_extract(args.extract_from)
        return

    known = set(INSTANCES) | set(SUBPAGES)
    ids = args.instance or sorted(known)
    unknown = [i for i in ids if i not in known]
    if unknown:
        fail("unknown instance(s): %s" % ", ".join(unknown))
    if not os.path.isdir(ENGINE_DIR):
        fail("engine/ does not exist — run --extract-from <instance> once to create it")

    drift, checked = [], 0
    for _instance, rel in targets(ids):
        target = os.path.join(REPO_ROOT, rel)
        current = read(target)
        composed = splice(current, rel)
        checked += 1
        if args.check:
            if current != composed:
                drift.append((rel, current, composed))
        elif current != composed:
            write(target, composed)
            print("compose-app: %s — engine blocks recomposed" % rel)
        else:
            print("compose-app: %s — already matches the shared engine" % rel)

    if args.check:
        if drift:
            for rel, cur, new in drift:
                print("compose-app: DRIFT in %s:" % rel, file=sys.stderr)
                for dl in list(difflib.unified_diff(
                        cur.splitlines(), new.splitlines(),
                        fromfile="committed", tofile="shared engine",
                        lineterm="", n=1))[:40]:
                    print("  " + dl, file=sys.stderr)
            fail("%d file(s) carry an ENGINE block that differs from engine/. "
                 "Edit the block in engine/ and recompose; an ENGINE fence inside "
                 "an instance file is not the source." % len(drift))
        print("compose-app: OK — %d file(s) across %d instance(s) carry exactly the "
              "shared engine" % (checked, len(ids)))
    else:
        print("compose-app: %d file(s) composed across %d instance(s)"
              % (checked, len(ids)))


if __name__ == "__main__":
    main()
