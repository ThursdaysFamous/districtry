#!/usr/bin/env python3
"""
Wait for a pull request's automated checks, and say how they ended.

WHY THIS EXISTS (2026-11-15). On an election night the results update merges
its own pull request once the checks pass
(.github/workflows/update-chicago-city-election-results.yml), so the job has to
know when they have passed. Three things on this repository make the obvious
ways of asking wrong, and each is recorded in CLAUDE.md from a time it misled
someone:

  - The gates are WORKFLOW RUNS. The commit-status API answers nothing for
    them, and the one commit status this repository does get (Deno's
    "deploy/districtry") is ignored by standing rule, so `gh pr checks`, which
    reads both, can fail a pull request whose gates all passed. This reads the
    workflow runs for the pull request's head commit and nothing else.
  - A zero read minutes after a push is a race, not an answer: a run is created
    some seconds after the push that starts it. So no run at all means "wait"
    until `--appear` seconds have passed, and only then "absent".
  - A pull request opened with the default workflow token starts no run at
    all (GitHub suppresses the recursive trigger), and so does one that
    conflicts with main. "Absent" is that state. It is never read as passed.

The answer is "green" only when the run of every workflow named with
`--require` exists for that commit and every run for it has completed with
success (or was skipped), seen twice in a row a poll apart, since a second
workflow's run can be created a moment after the first one's.

    python3 scripts/wait_for_pr_checks.py --sha <head commit> --require smoke-test.yml
    python3 scripts/wait_for_pr_checks.py --selftest

Exit codes: 0 green; 1 red (a run failed, was cancelled or timed out); 3 absent
(no run started); 4 the wait ran out with runs still going. It reads through
the `gh` CLI, as the workflows do, with whatever GH_TOKEN the step gives it.
"""

import argparse
import json
import os
import subprocess
import sys
import time

GOOD = ("success", "skipped", "neutral")
EXIT = {"green": 0, "red": 1, "absent": 3, "timeout": 4}


def decide(runs, required, waited, appear):
    """("green" | "red" | "wait" | "absent", why) from the workflow runs of one
    commit. `runs` are the API's run objects ({path, status, conclusion,
    event, ...}); `required` are workflow file names that must have a run;
    `waited` is the seconds waited so far and `appear` how long a run may take
    to be created."""
    runs = [r for r in runs if r.get("event") in ("pull_request", "pull_request_target")]
    names = set(os.path.basename(r.get("path") or "") for r in runs)
    missing = [w for w in required if w not in names]
    bad = [r for r in runs if r.get("status") == "completed" and r.get("conclusion") not in GOOD]
    if bad:
        return "red", "; ".join("%s ended %s" % (os.path.basename(r.get("path") or "?"),
                                                r.get("conclusion")) for r in bad)
    if missing:
        if waited >= appear:
            return "absent", "no run of %s started on this commit" % ", ".join(missing)
        return "wait", "no run of %s yet" % ", ".join(missing)
    going = [r for r in runs if r.get("status") != "completed"]
    if going:
        return "wait", "%d of %d run(s) still going" % (len(going), len(runs))
    return "green", "%d run(s) completed: %s" % (len(runs), ", ".join(sorted(names)))


def runs_for(repo, sha):
    r = subprocess.run(
        ["gh", "api", "--paginate", "--jq", ".workflow_runs[]",
         "repos/%s/actions/runs?head_sha=%s&per_page=100" % (repo, sha)],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or "gh api failed")
    return [json.loads(line) for line in r.stdout.splitlines() if line.strip()]


def selftest():
    def run(path, status, conclusion=None, event="pull_request"):
        return {"path": ".github/workflows/" + path, "status": status,
                "conclusion": conclusion, "event": event}
    req = ["smoke-test.yml"]
    cases = [
        (decide([], req, 30, 600)[0] == "wait", "no run yet, early, is a wait"),
        (decide([], req, 600, 600)[0] == "absent", "no run after the allowance is absent"),
        (decide([run("smoke-test.yml", "completed", "success", "push")], req, 700, 600)[0] == "absent",
         "a push run of the same commit is not the pull request's"),
        (decide([run("smoke-test.yml", "in_progress")], req, 60, 600)[0] == "wait",
         "the gate still going is a wait"),
        (decide([run("smoke-test.yml", "queued")], req, 60, 600)[0] == "wait", "a queued run is a wait"),
        (decide([run("smoke-test.yml", "completed", "success")], req, 900, 600)[0] == "green",
         "the gate passed"),
        (decide([run("smoke-test.yml", "completed", "success"),
                 run("vector-tiles.yml", "in_progress")], req, 900, 600)[0] == "wait",
         "another workflow still going is a wait"),
        (decide([run("smoke-test.yml", "completed", "success"),
                 run("vector-tiles.yml", "completed", "skipped")], req, 900, 600)[0] == "green",
         "a skipped run does not hold it"),
        (decide([run("smoke-test.yml", "in_progress"),
                 run("files-host.yml", "completed", "failure")], req, 60, 600)[0] == "red",
         "a failed run is red at once, whatever is still going"),
        (decide([run("smoke-test.yml", "completed", "cancelled")], req, 900, 600)[0] == "red",
         "a cancelled gate is red"),
        (decide([run("smoke-test.yml", "completed", "timed_out")], req, 900, 600)[0] == "red",
         "a timed-out gate is red"),
        (decide([run("vector-tiles.yml", "completed", "success")], req, 900, 600)[0] == "absent",
         "another workflow passing does not stand in for the gate"),
        (decide([run("vector-tiles.yml", "completed", "success")], [], 0, 600)[0] == "green",
         "with no gate named, the runs there are decide it"),
    ]
    bad = [why for ok, why in cases if not ok]
    for why in bad:
        print("wait-for-pr-checks: selftest FAIL — " + why, file=sys.stderr)
    if bad:
        raise SystemExit(1)
    print("wait-for-pr-checks: selftest OK — %d cases of a commit's workflow runs" % len(cases))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--sha", help="the pull request's head commit")
    ap.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"))
    ap.add_argument("--require", action="append", default=[], metavar="WORKFLOW.yml",
                    help="a workflow that must have run on the commit; give each once")
    ap.add_argument("--appear", type=int, default=600,
                    help="seconds a run may take to be created before it counts as absent")
    ap.add_argument("--timeout", type=int, default=3000, help="seconds to wait in all")
    ap.add_argument("--poll", type=int, default=30)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not args.sha or not args.repo:
        ap.error("--sha and --repo (or GITHUB_REPOSITORY) are required")

    start = time.time()
    green_before = False
    errors = 0
    while True:
        waited = time.time() - start
        try:
            verdict, why = decide(runs_for(args.repo, args.sha), args.require, waited, args.appear)
            errors = 0
        except (RuntimeError, ValueError) as exc:
            # one failed read of the API is not an answer about the checks
            errors += 1
            verdict, why = "wait", "could not read the runs (%s)" % exc
            if errors >= 5:
                print("wait-for-pr-checks: the runs could not be read five times in a row: %s"
                      % exc, file=sys.stderr)
                raise SystemExit(EXIT["timeout"])
        print("wait-for-pr-checks: %4ds %s — %s" % (waited, verdict, why), flush=True)
        if verdict == "green":
            if green_before:
                raise SystemExit(EXIT["green"])
            green_before = True
        else:
            green_before = False
            if verdict in ("red", "absent"):
                raise SystemExit(EXIT[verdict])
        if waited >= args.timeout:
            print("wait-for-pr-checks: gave up after %d seconds" % waited, file=sys.stderr)
            raise SystemExit(EXIT["timeout"])
        time.sleep(args.poll)


if __name__ == "__main__":
    main()
