#!/usr/bin/env python3
"""
The steward skill runs the same battery CI does — compared, not asserted.

WHY. CLAUDE.md has claimed since 2026-09-12 that
`.claude/skills/steward/SKILL.md` mirrors `.github/workflows/smoke-test.yml`
exactly, so an agent driving a pull request to green locally runs what the merge
gate will run. Nothing compared them. On 2026-09-16 the skill was missing three
gates — `build_about_page.py --check`, `validate_analytics.py` and
`build_il_gis_board_rosters.py --check` — all three wired into CI on the same day
that exact-mirror sentence was written and none of them added to the skill. An
agent following the skill would have run a battery that passed and pushed a
branch the merge gate failed, which is the one thing the skill exists to prevent.

WHAT IT COMPARES. Every `python3` or `node` command line in each file, as a
multiset, both ways. Four normalisations, each for a stated reason:

  * a trailing `# rationale` comment is the skill's whole point and is stripped;
  * `|| status=1` is the workflow's way of running all ten browser gates before
    failing, and is not part of the command;
  * a leading `VAR=value` prefix (`BASE_URL=…`) is stripped, because the skill
    documents the URL a reader serves on rather than the runner's;
  * `"$BASE"` is the workflow's shell variable for the branch point, which the
    skill spells `origin/main`.

WHAT IT DELIBERATELY DOES NOT COMPARE. Order. The skill groups by what a reader
is fixing; CI orders by cost. A gate present in both in a different place is
mirrored. What matters is that neither file can run something the other does not.

`python3 -m http.server`, which serves the pages to the browser gates rather
than testing anything, is excluded from both sides.

    python3 scripts/validate_steward_mirror.py
"""

import collections
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOW = os.path.join(REPO_ROOT, ".github", "workflows", "smoke-test.yml")
SKILL = os.path.join(REPO_ROOT, ".claude", "skills", "steward", "SKILL.md")

INVOCATION = re.compile(r"^(?:python3|node)\s+\S+")
ENV_PREFIX = re.compile(r"^(?:[A-Z_]+=\S+\s+)+")


def fail(msg):
    print("validate-steward-mirror: FAIL — %s" % msg, file=sys.stderr)
    sys.exit(1)


def invocations(path, strip_comment):
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            text = line.strip()
            if strip_comment:
                text = text.split("#")[0].strip()
            text = re.sub(r"^run:\s*", "", text)
            text = ENV_PREFIX.sub("", text)
            if not INVOCATION.match(text) or "http.server" in text:
                continue
            text = text.split("||")[0].strip()
            out.append(re.sub(r"\s+", " ", text).replace('"$BASE"', "origin/main"))
    return out


def main():
    ci = collections.Counter(invocations(WORKFLOW, strip_comment=False))
    skill = collections.Counter(invocations(SKILL, strip_comment=True))
    if not ci or not skill:
        fail("read %d invocation(s) from the workflow and %d from the skill — "
             "one of the two files has changed shape" % (sum(ci.values()),
                                                         sum(skill.values())))
    missing = sorted((ci - skill).elements())
    extra = sorted((skill - ci).elements())
    if missing:
        fail("the steward skill does not run %d gate(s) CI does: %s"
             % (len(missing), "; ".join(missing)))
    if extra:
        fail("the steward skill runs %d gate(s) CI does not: %s — either wire "
             "them into smoke-test.yml or drop them from the skill"
             % (len(extra), "; ".join(extra)))
    print("validate-steward-mirror: OK — %d invocation(s) for %d, compared both "
          "ways as multisets" % (sum(ci.values()), sum(skill.values())))


if __name__ == "__main__":
    main()
