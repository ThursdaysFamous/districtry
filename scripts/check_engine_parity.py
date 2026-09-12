#!/usr/bin/env python3
"""
Cross-metro engine parity check.

Every District Explorer metro is its own fork (see docs/ENGINE_SYNC.md), but
the metro-agnostic "engine" inside index.html is meant to be byte-identical
across forks. Shared code is fenced with marker comments:

    /* ==== ENGINE:BEGIN block-name ==== */
    ...shared code, byte-identical in every fork...
    /* ==== ENGINE:END block-name ==== */

(HTML regions use the same markers inside <!-- ... --> comments.) Everything
metro-specific that engine blocks reference lives in the METRO config block
near the top of the script, so an engine block never needs a per-city edit.

This script is itself part of the shared engine: the SAME file ships in every
fork. Per-fork values (which sibling to compare against) are passed on the
command line by each fork's workflow, never hardcoded here.

Modes:
  Lint (default) — markers are balanced, non-nested, uniquely named:
      python3 scripts/check_engine_parity.py index.html

  Compare — same blocks, byte-identical bodies, against a sibling fork's
  index.html (a local path or a deployed URL):
      python3 scripts/check_engine_parity.py index.html \
          --against https://nyc.chidistricts.com/ [--label nyc]

  Post-assembly assertion — compare this file's blocks against a downloaded
  engine release (docs/MECHANIZATION_PLAYBOOK.md, Conversion 1). Reads the
  manifest, takes the blocks it assigns to this file's basename, and compares
  them byte-wise against the bundle. Run with --strict inside the deploy job,
  right after apply_engine.py, so a splice that doesn't reproduce the pinned
  engine fails the deploy:
      python3 scripts/check_engine_parity.py index.html \
          --against-bundle engine.manifest.json --strict

Exit codes: 0 = ok (or drift found without --strict; drift is a WARN that a
human ports, matching validate_sources.py's "surface, don't block" pattern),
1 = hard FAIL (malformed markers, unreadable input), 2 = drift with --strict.
--report FILE writes a markdown report; --status-file FILE writes ok|warn|fail.
"""

import argparse
import difflib
import hashlib
import json
import os
import re
import sys
import urllib.request

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE_DIR = os.path.join(REPO_ROOT, "engine")

MARKER_RE = re.compile(
    r"^[ \t]*(?:/\*|<!--)[ \t]*==== ENGINE:(BEGIN|END) ([a-z0-9][a-z0-9-]*) ====[ \t]*(?:\*/|-->)[ \t]*$"
)


def read_source(spec):
    """Read text from a local path or an http(s) URL."""
    if spec.startswith("http://") or spec.startswith("https://"):
        req = urllib.request.Request(spec, headers={"User-Agent": "districtry-engine-parity"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8")
    with open(spec, encoding="utf-8") as f:
        return f.read()


def extract_blocks(text, label):
    """Return {name: body} for every ENGINE block. Raises ValueError on
    malformed fences (unbalanced, nested, duplicate names, END/BEGIN mismatch).
    Bodies exclude the marker lines themselves, so JS vs HTML comment style
    never affects comparison."""
    blocks = {}
    open_name = None
    body = []
    for lineno, line in enumerate(text.splitlines(), 1):
        m = MARKER_RE.match(line)
        if not m:
            if open_name is not None:
                body.append(line)
            continue
        kind, name = m.groups()
        if kind == "BEGIN":
            if open_name is not None:
                raise ValueError(
                    "%s:%d: ENGINE:BEGIN %s while %s is still open (nesting is not allowed)"
                    % (label, lineno, name, open_name)
                )
            if name in blocks:
                raise ValueError("%s:%d: duplicate ENGINE block name %r" % (label, lineno, name))
            open_name = name
            body = []
        else:
            if open_name is None:
                raise ValueError("%s:%d: ENGINE:END %s without a matching BEGIN" % (label, lineno, name))
            if name != open_name:
                raise ValueError(
                    "%s:%d: ENGINE:END %s does not match open block %s" % (label, lineno, name, open_name)
                )
            blocks[open_name] = "\n".join(body)
            open_name = None
    if open_name is not None:
        raise ValueError("%s: ENGINE block %s is never closed" % (label, open_name))
    return blocks


def digest(body):
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:12]


def blocks_from_bundle(manifest_path, target_file):
    """Return ({name: body}, label) for the blocks an engine-release manifest
    assigns to target_file's basename, read out of the bundle it describes.
    The bundle re-wraps every block in the same fence markers, so the one
    shared parser reads it back. Raises ValueError on a manifest whose block
    list and bundle contents disagree — that is a corrupt artifact, never a
    porting WARN."""
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    bundle_path = os.path.join(os.path.dirname(manifest_path) or ".", manifest["bundle"])
    with open(bundle_path, encoding="utf-8") as f:
        bundle_blocks = extract_blocks(f.read(), bundle_path)
    wanted = {}
    base = os.path.basename(target_file)
    for entry in manifest["blocks"]:
        if entry["file"] != base:
            continue
        if entry["name"] not in bundle_blocks:
            raise ValueError(
                "%s: manifest lists block %r for %s but the bundle does not contain it"
                % (manifest_path, entry["name"], base)
            )
        wanted[entry["name"]] = bundle_blocks[entry["name"]]
    if not wanted:
        raise ValueError(
            "%s: manifest assigns no blocks to %r — wrong target file?" % (manifest_path, base)
        )
    return wanted, "bundle %s (%s)" % (manifest.get("engine_version", "?"), manifest_path)


def short_diff(name, ours, theirs, ours_label, theirs_label, max_lines=24):
    lines = list(
        difflib.unified_diff(
            ours.splitlines(), theirs.splitlines(),
            fromfile="%s %s" % (ours_label, name), tofile="%s %s" % (theirs_label, name),
            lineterm="", n=1,
        )
    )
    clipped = lines[:max_lines]
    if len(lines) > max_lines:
        clipped.append("... (%d more diff lines)" % (len(lines) - max_lines))
    return "\n".join(clipped)


def discover_surfaces():
    """[(surface, relative path)] for every authored file that can carry fences.

    The TREE is canonical, never a table: an instance is a top-level directory
    with its own index.html and data/app/, the same rule
    scripts/validate_instance_registration.py discovers by, because a table
    would let this gate agree with itself about an instance nobody registered.
    `root` is the pseudo-surface for the repo-root pages (the landing page, the
    service-worker kill switch, and the shared sub-pages), which carry fences
    too and compose exactly as the instances' do.
    """
    insts = sorted(
        d for d in os.listdir(REPO_ROOT)
        if os.path.isdir(os.path.join(REPO_ROOT, d))
        and os.path.exists(os.path.join(REPO_ROOT, d, "index.html"))
        and os.path.isdir(os.path.join(REPO_ROOT, d, "data", "app"))
    )
    out = []
    for surface in ["root"] + insts:
        prefix = "" if surface == "root" else surface + "/"
        here = os.path.join(REPO_ROOT, prefix) if prefix else REPO_ROOT
        names = sorted(f for f in os.listdir(here) if f.endswith(".html"))
        if os.path.exists(os.path.join(here, "sw.js")):
            names.append("sw.js")
        for name in names:
            out.append((surface, prefix + name))
    return insts, out


def group_key(basename, name):
    """The key two occurrences of a block must share to be ONE block.

    This mirrors scripts/compose_app.py's block_path(): a name with a source at
    engine/shared/ is spliced from that ONE file into several basenames, so it
    is keyed by NAME alone; anything else is keyed per basename. Keying a
    shared block per basename would compare il/faq.html against ny/faq.html and
    never compare either against il/sources.html, which is spliced from the
    same source.
    """
    if os.path.exists(os.path.join(ENGINE_DIR, "shared", name + ".txt")):
        return "shared:" + name
    return "%s:%s" % (basename, name)


def run_fleet():
    """Compare every fence interior across every surface, and report the
    blocks only some instances carry.

    Two different jobs, deliberately with two different severities.

    DRIFT between instances is a hard FAIL. It is also belt-and-braces behind
    `compose_app.py --check`, which proves each file carries exactly the bytes
    in engine/ and therefore makes cross-instance drift impossible while it
    passes. This catches the case where both are edited together, and costs one
    pass over 51 files.

    THE PRESENCE INVENTORY only ever REPORTS, because a block legitimately
    lives in some instances and not others: `county-layer-dispatcher` is in il,
    ia and mi and absent from ca, ny and wi by design, since those three
    register no county-dispatched concept. Nothing measured that before, and
    compose_app cannot: it splices by MARKER PRESENCE, so a file with no fence
    for a block is not wrong, it is simply not asked. An absence is stated here
    so a reader sees the shape rather than inferring it from a fence count.
    """
    insts, surfaces = discover_surfaces()
    if len(insts) < 2:
        print("engine-parity: FAIL — discovered %d instance(s) (%s); expected at least two, so "
              "the discovery rule is broken rather than the tree"
              % (len(insts), ", ".join(insts) or "none"), file=sys.stderr)
        return 1

    groups = {}          # key -> {surface: (body, path)}
    for surface, rel in surfaces:
        path = os.path.join(REPO_ROOT, rel)
        try:
            found = extract_blocks(read_source(path), rel)
        except (ValueError, OSError) as e:
            print("engine-parity: FAIL — %s" % e, file=sys.stderr)
            return 1
        for name, body in found.items():
            groups.setdefault(group_key(os.path.basename(rel), name), {})[surface] = (body, rel)

    drifted = []
    for key in sorted(groups):
        bodies = {s: b for s, (b, _) in groups[key].items()}
        if len(set(bodies.values())) > 1:
            drifted.append(key)

    partial = []
    for key in sorted(groups):
        have = set(groups[key]) & set(insts)
        if not have:
            continue                      # root-only block; no instance claim to make
        absent = sorted(set(insts) - have)
        if absent:
            partial.append((key, sorted(have), absent))

    print("engine-parity: %s — %d block group(s) across %d file(s), %d instance(s) (%s) + root"
          % ("FAIL" if drifted else "OK", len(groups), len(surfaces), len(insts), ", ".join(insts)))

    if partial:
        print("  blocks some instances carry and others do not (reported, never failed):")
        for key, have, absent in partial:
            print("    %-44s have: %-24s absent: %s"
                  % (key, ",".join(have), ",".join(absent)))
    else:
        print("  every block group is carried by every instance that has its file")

    for key in drifted:
        per = groups[key]
        first = sorted(per)[0]
        print("  DRIFT %s" % key, file=sys.stderr)
        for s in sorted(per):
            body, rel = per[s]
            print("    %-6s %s  %s" % (s, digest(body), rel), file=sys.stderr)
        for s in sorted(per):
            if per[s][0] != per[first][0]:
                print(short_diff(key, per[first][0], per[s][0], first, s), file=sys.stderr)
                break
    if drifted:
        print("engine-parity: FAIL — %d block group(s) differ between instances; edit the block "
              "under engine/ and run scripts/compose_app.py, never a fence inside an instance file"
              % len(drifted), file=sys.stderr)
        return 1
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", nargs="?", default="index.html", help="this fork's index.html")
    ap.add_argument("--against", help="sibling index.html: local path or deployed URL")
    ap.add_argument("--fleet", action="store_true",
                    help="compare every fence interior across every instance discovered "
                         "from the tree, and report the blocks only some carry")
    ap.add_argument("--against-bundle", metavar="MANIFEST",
                    help="engine.manifest.json of a downloaded release: compare this file's "
                         "blocks against the bundle (post-assembly assertion; use with --strict)")
    ap.add_argument("--label", default=None, help="short name for the sibling in the report")
    ap.add_argument("--report", help="write a markdown report to this path")
    ap.add_argument("--status-file", help="write ok|warn|fail to this path")
    ap.add_argument("--strict", action="store_true", help="exit 2 on drift (for local pre-port checks)")
    args = ap.parse_args()

    if args.fleet:
        sys.exit(run_fleet())

    status = "ok"
    report = []

    try:
        ours = extract_blocks(read_source(args.file), args.file)
    except (ValueError, OSError) as e:
        print("engine-parity: FAIL — %s" % e, file=sys.stderr)
        if args.status_file:
            open(args.status_file, "w").write("fail")
        sys.exit(1)

    if not ours:
        print("engine-parity: FAIL — %s contains no ENGINE blocks" % args.file, file=sys.stderr)
        if args.status_file:
            open(args.status_file, "w").write("fail")
        sys.exit(1)

    if args.against and args.against_bundle:
        print("engine-parity: FAIL — --against and --against-bundle are mutually exclusive", file=sys.stderr)
        sys.exit(1)

    if not args.against and not args.against_bundle:
        print("engine-parity: OK — %d ENGINE blocks, markers well formed:" % len(ours))
        for name in sorted(ours):
            print("  %-28s %s  (%d lines)" % (name, digest(ours[name]), ours[name].count("\n") + 1))
        if args.status_file:
            open(args.status_file, "w").write("ok")
        return

    if args.against_bundle:
        # Post-assembly assertion: a release artifact that is unreadable or
        # self-inconsistent is a hard FAIL, never a porting WARN — the deploy
        # must stop, not open an issue.
        try:
            theirs, sibling_label = blocks_from_bundle(args.against_bundle, args.file)
        except (ValueError, OSError, KeyError) as e:
            print("engine-parity: FAIL — %s" % e, file=sys.stderr)
            if args.status_file:
                open(args.status_file, "w").write("fail")
            sys.exit(1)
        if args.label:
            sibling_label = args.label
    else:
        sibling_label = args.label or args.against
        try:
            theirs = extract_blocks(read_source(args.against), sibling_label)
        except (ValueError, OSError) as e:
            # A sibling that hasn't shipped markers yet (or is unreachable) is a
            # WARN, not a FAIL: surface it, let a human decide.
            print("engine-parity: WARN — could not extract sibling blocks: %s" % e, file=sys.stderr)
            report.append("## Sibling `%s`\n\n**Could not extract ENGINE blocks:** %s\n" % (sibling_label, e))
            status = "warn"
            theirs = {}

    if args.against and not theirs and status == "ok":
        # Readable, well-formed source with zero fences: the sibling hasn't
        # shipped the marked engine yet (e.g. the parity release is merged but
        # not deployed there). Surface it — silence would read as parity.
        print("engine-parity: WARN — sibling %s contains no ENGINE blocks (markers not shipped yet?)" % sibling_label,
              file=sys.stderr)
        report.append("## Sibling `%s`\n\n**No ENGINE blocks found** — the sibling has not shipped the fenced engine yet (merged but undeployed?), or its fences were deleted.\n" % sibling_label)
        status = "warn"

    ok, drifted, missing_theirs, missing_ours = [], [], [], []
    if theirs:
        for name in sorted(set(ours) | set(theirs)):
            if name not in theirs:
                missing_theirs.append(name)
            elif name not in ours:
                missing_ours.append(name)
            elif ours[name] == theirs[name]:
                ok.append(name)
            else:
                drifted.append(name)
        if drifted or missing_theirs or missing_ours:
            status = "warn"

        report.append("## Sibling `%s`\n" % sibling_label)
        report.append("| status | blocks |")
        report.append("|---|---|")
        report.append("| identical | %d |" % len(ok))
        report.append("| **drifted** | %s |" % (", ".join("`%s`" % n for n in drifted) or "—"))
        report.append("| missing in sibling | %s |" % (", ".join("`%s`" % n for n in missing_theirs) or "—"))
        report.append("| missing here | %s |" % (", ".join("`%s`" % n for n in missing_ours) or "—"))
        report.append("")
        for name in drifted:
            report.append("### drift in `%s`\n" % name)
            report.append("```diff")
            report.append(short_diff(name, ours[name], theirs[name], args.file, sibling_label))
            report.append("```\n")

    print("engine-parity: %s — %d identical, %d drifted, %d missing in sibling, %d missing here"
          % (status.upper(), len(ok), len(drifted), len(missing_theirs), len(missing_ours)))
    for name in drifted:
        print("  DRIFT   %s" % name)
    for name in missing_theirs:
        print("  THEIRS? %s (not in sibling)" % name)
    for name in missing_ours:
        print("  OURS?   %s (sibling has it, we don't)" % name)

    if args.report:
        header = (
            "# Engine parity report\n\n"
            "Byte-level comparison of `ENGINE` blocks (see `docs/ENGINE_SYNC.md`). "
            "Drift means one fork's engine changed without the diff being ported to the sibling — "
            "port the missing commit(s); never re-implement from a prose prompt.\n\n"
        )
        open(args.report, "w").write(header + "\n".join(report) + "\n")
    if args.status_file:
        open(args.status_file, "w").write(status)
    if status != "ok" and args.strict:
        sys.exit(2)


if __name__ == "__main__":
    main()
