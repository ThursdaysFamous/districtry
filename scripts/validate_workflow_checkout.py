#!/usr/bin/env python3
"""Merge gate: a workflow that regenerates and commits sitemap.xml must check
out the FULL history, and must not re-shallow it afterwards.

WHY THIS EXISTS. `build_sitemap.py` takes each page's lastmod from that file's
own last commit. In a depth-1 clone there is only one commit, so git reports it
as the last commit of EVERY file and all 243 entries take the run date. On
2026-09-17 a bot roster run shipped 241 wrong dates that way, and on 2026-09-19
73 scheduled workflows were still built to do it again — every weekly roster
refresh in the fleet bar ten.

Nothing caught it, and the reason is worth stating because it is the general
shape. `build_sitemap.py --check` compares the shipped file against a rebuild
and fails when an entry is STALE — behind the file's real last commit. A
shallow clone moves every date FORWARD, to today, which is never stale. So the
check that owns this file is structurally blind to the defect, and passes on
the very run that introduces it.

WHAT IT CHECKS, per workflow file, offline and stdlib-only:

  1. A workflow whose commit stages `sitemap.xml` must set `fetch-depth: 0` on
     its `actions/checkout` step.
  2. That workflow must not run `git fetch --depth=...`. A depth-limited fetch
     RE-SHALLOWS a clone that was checked out complete — measured on this repo,
     512 commits down to 13 — so deepening the checkout alone is undone at the
     branch cut, and the two have to move together. This is the half that looks
     correct in a diff and is not.

WHAT IT DOES NOT CATCH, so nobody over-trusts the OK line. It reads the workflow
text, not a run: a job that reaches sitemap.xml through a script or a composite
action rather than a literal `git add` line is invisible to it, as is one that
shallows the clone by some route other than `--depth`. And it says nothing about
whether the dates the sitemap ends up with are RIGHT — only that the job was
given the history it needs to compute them.
"""
import re
import sys
from pathlib import Path

WORKFLOWS = Path(".github/workflows")

STAGES_SITEMAP = re.compile(r"git add[^\n]*\bsitemap\.xml\b")
FULL_DEPTH = re.compile(r"^\s*fetch-depth:\s*0\s*$", re.M)
SHALLOW_FETCH = re.compile(r"git fetch[^\n]*--depth")


def main() -> int:
    if not WORKFLOWS.is_dir():
        print("validate-workflow-checkout: FAIL — %s not found" % WORKFLOWS, file=sys.stderr)
        return 1

    paths = sorted(WORKFLOWS.glob("*.yml")) + sorted(WORKFLOWS.glob("*.yaml"))
    if not paths:
        print("validate-workflow-checkout: FAIL — no workflow files found", file=sys.stderr)
        return 1

    errors = []
    checked = 0
    for path in paths:
        text = path.read_text()
        if not STAGES_SITEMAP.search(text):
            continue
        checked += 1
        if not FULL_DEPTH.search(text):
            errors.append(
                "%s commits sitemap.xml but does not set `fetch-depth: 0` on its "
                "checkout — every lastmod in the file it writes will take the run "
                "date" % path.name
            )
        if SHALLOW_FETCH.search(text):
            errors.append(
                "%s commits sitemap.xml and runs a depth-limited `git fetch`, "
                "which re-shallows the clone the checkout deepened — drop the "
                "--depth flag" % path.name
            )

    if not checked:
        print(
            "validate-workflow-checkout: FAIL — no workflow stages sitemap.xml, so "
            "this gate is checking nothing; if that is a real change, retire it "
            "rather than leaving it green",
            file=sys.stderr,
        )
        return 1

    if errors:
        print("validate-workflow-checkout: FAIL", file=sys.stderr)
        for err in errors:
            print("  - %s" % err, file=sys.stderr)
        return 1

    print(
        "validate-workflow-checkout: OK — %d workflow(s) commit sitemap.xml, every "
        "one on a full-history checkout with no re-shallowing fetch" % checked
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
