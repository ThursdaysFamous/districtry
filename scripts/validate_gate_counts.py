#!/usr/bin/env python3
"""
CLAUDE.md states how big this battery is; nothing measured it.

WHY. The "Running & testing" section states the battery's size twice — as
NAMED STEPS and as SCRIPT INVOCATIONS — and that pair moves whenever anything
merges into `.github/workflows/smoke-test.yml`. Its own paragraph records the
figure going stale seven times in two days, and CLAUDE.md's instruction is to
re-measure rather than increment. Nothing enforced that, so the pair was
re-derived by ARITHMETIC on a figure that was itself wrong: measured against
this repository's own history on 2026-09-18, the tree was 48/73 at #951 and
49/74 at the redirect-shells commit and 59/84 at #977, so the sentence saying
a branch "adds four of each — so it stood at 55/80" described a state no
commit ever had. Every one of those numbers was in git the whole time.

WHAT IT MEASURES, which is CLAUDE.md's own stated rule:

  * a static gate is one NAMED step in the `smoke` job ahead of the
    `actions/setup-node` step;
  * an invocation is a `python3` or `node` command line in that job, excluding
    `python3 -m http.server`, which serves the pages to the browser gates
    rather than testing anything, and excluding the `npx playwright install`
    lines, which are setup and are not commands of either kind;
  * an invocation boots Chromium if it is a `node` command AFTER the
    setup-node step. `scripts/build_og_image.mjs --check` is the reason that
    is a position test and not a name test: it is a `node` command that
    imports playwright through a dynamic `await import()` inside `render()`,
    which `--check` never reaches, and it runs BEFORE Playwright is installed.

TWO PARSES, COMPARED. `validate_steward_mirror.py` already reads this
workflow's invocations, for a different question. Re-deriving them here would
make two readers of one question, which is where this fleet's recurring defect
starts — so this gate asserts its own invocation total against that module's,
and FAILS when they disagree. A disagreement means one of the two readings is
wrong about a command CI runs, which is the case neither can see alone.

IT CANNOT PASS VACUOUSLY. The figures live in prose, and the same section
deliberately records SUPERSEDED figures ("the 59/84 this paragraph carried on
2026-09-16") that must never be rewritten. So each live figure is matched by
an anchor naming the claim it belongs to, and a missing anchor is a FAILURE
rather than a skip: a reworded sentence must come back through this gate, not
silently stop being checked.

    python3 scripts/validate_gate_counts.py
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import validate_steward_mirror as mirror                      # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOW = os.path.join(REPO_ROOT, ".github", "workflows", "smoke-test.yml")
CLAUDE_MD = os.path.join(REPO_ROOT, "CLAUDE.md")

INVOCATION = re.compile(r"^(?:python3|node)\s+\S+")
ENV_PREFIX = re.compile(r"^(?:[A-Z_]+=\S+\s+)+")

# Each live figure, with the anchor that identifies it. The anchors are matched
# against CLAUDE.md with its whitespace collapsed, because every one of these
# sentences wraps.
ANCHORS = [
    ("steps",
     r"one NAMED step in the `smoke` job ahead of the `actions/setup-node` "
     r"step, which is \*\*(\d+)\*\*"),
    ("invocations",
     r"the whole battery is \*\*(\d+) — (\d+) that need no browser and "
     r"(\d+) that boot Chromium\*\*"),
    ("mirror",
     r"mirrors it EXACTLY as of [\d-]+, \*\*(\d+)\s+invocations for (\d+)\*\*"),
]


def fail(msg):
    print("validate-gate-counts: FAIL — %s" % msg, file=sys.stderr)
    sys.exit(1)


def measure():
    """(named steps, invocations, no browser, Chromium) from the smoke job."""
    lines = open(WORKFLOW, encoding="utf-8").read().split("\n")
    head = next((i for i, l in enumerate(lines) if re.match(r"^\s*smoke:\s*$", l)),
                None)
    if head is None:
        fail("no `smoke:` job in %s — the workflow has changed shape"
             % os.path.relpath(WORKFLOW, REPO_ROOT))
    indent = len(re.match(r"^(\s*)", lines[head]).group(1))
    end = next((i for i in range(head + 1, len(lines))
                if lines[i].strip()
                and not lines[i].startswith(" " * (indent + 1))), len(lines))
    job = lines[head:end]

    setup = next((i for i, l in enumerate(job) if "actions/setup-node" in l), None)
    if setup is None:
        fail("the smoke job has no actions/setup-node step, which is the line "
             "the static and browser tiers are split at")

    steps = sum(1 for i, l in enumerate(job)
                if i < setup and l.strip().startswith("- name:"))

    invocations = []
    for i, line in enumerate(job):
        text = ENV_PREFIX.sub("", re.sub(r"^run:\s*", "", line.strip()))
        if not INVOCATION.match(text) or "http.server" in text:
            continue
        invocations.append((i, text.split("||")[0].strip()))
    chromium = sum(1 for i, t in invocations
                   if i > setup and t.startswith("node "))
    return steps, len(invocations), len(invocations) - chromium, chromium


def stated():
    text = re.sub(r"\s+", " ", open(CLAUDE_MD, encoding="utf-8").read())
    out = {}
    for key, pattern in ANCHORS:
        found = re.findall(pattern, text)
        if not found:
            fail("CLAUDE.md no longer carries the %r claim this gate checks. "
                 "It was reworded or removed rather than corrected — restore a "
                 "sentence this pattern matches, or change the pattern in the "
                 "same commit:\n    %s" % (key, pattern))
        if len(found) > 1:
            fail("CLAUDE.md states the %r claim %d times; this gate checks one "
                 "live figure per claim and cannot tell which is current"
                 % (key, len(found)))
        out[key] = tuple(int(n) for n in
                         (found[0] if isinstance(found[0], tuple) else (found[0],)))
    return out


def main():
    steps, total, no_browser, chromium = measure()

    cross = len(mirror.invocations(WORKFLOW, strip_comment=False))
    if cross != total:
        fail("this gate reads %d invocation(s) in the smoke job and "
             "validate_steward_mirror.py reads %d in the same file. One of the "
             "two readings is wrong about a command CI runs." % (total, cross))

    said = stated()
    problems = []
    if said["steps"][0] != steps:
        problems.append("named steps: CLAUDE.md says %d, the workflow has %d"
                        % (said["steps"][0], steps))
    if said["invocations"] != (total, no_browser, chromium):
        problems.append("invocations: CLAUDE.md says %d — %d no browser, %d "
                        "Chromium; the workflow has %d — %d and %d"
                        % (said["invocations"] + (total, no_browser, chromium)))
    if said["mirror"] != (total, total):
        problems.append("the steward-mirror sentence says %d invocations for "
                        "%d; the battery is %d" % (said["mirror"] + (total,)))

    if problems:
        fail("CLAUDE.md's stated battery size no longer matches "
             ".github/workflows/smoke-test.yml:\n    %s\n\n  Re-measure rather "
             "than increment, and state the date. The figures are:\n"
             "    named steps ahead of actions/setup-node : %d\n"
             "    invocations                             : %d"
             " (%d no browser, %d Chromium)"
             % ("\n    ".join(problems), steps, total, no_browser, chromium))

    print("validate-gate-counts: OK — CLAUDE.md states %d named static step(s) "
          "and %d invocation(s) (%d no browser, %d Chromium), which is what "
          "the smoke job runs; both invocation readings agree"
          % (steps, total, no_browser, chromium))


if __name__ == "__main__":
    main()
