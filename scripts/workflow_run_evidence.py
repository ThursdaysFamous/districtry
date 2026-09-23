#!/usr/bin/env python3
"""
Which of a workflow's runs are evidence about whether it is still refreshing.

TWO SCRIPTS ASK THIS QUESTION and until 2026-09-23 each answered it alone, which
is where this fleet's recurring defect starts. `check_roster_workflow_health.py`
writes the roster-health issue (#387) and `fleet_status.py` writes the weekly
fleet issue (#138); both take a workflow's newest completed run and report its
conclusion as that workflow's health. Neither asked whether the run it picked
was a run at all.

WHAT A RUN THAT NEVER STARTED LOOKS LIKE. When GitHub cannot read a workflow
file at a commit it still records a run against that workflow, and that run
carries a conclusion of "failure" with NO JOB EVER STARTED. Measured 2026-09-23
on four such runs and their healthy neighbours:

    35782165269  update-mps-school-board-roster.yml   push    claude/goat-counter-
                 data-access-g5ycax   failure   0 jobs   created==updated
                 name ".github/workflows/update-mps-school-board-roster.yml"
    35648845084  the same workflow    schedule  main     success  12s elapsed
                 name "Update MPS school board roster"

Nothing was scraped in the first and no step ran, so it says nothing about the
roster. It is a failure to PARSE A COPY OF THE WORKFLOW FILE, and in that case
the copy was a stale one on a branch cut before the repair in #978 and since
deleted from origin — so it could not be superseded, and #387 and #138 both
carried it as a FAILING roster refresh that would repeat every week.

THE BRANCH IS NOT THE TEST, and a first draft of this fix had it wrong. Run
35166293478 is the same shape ON MAIN, from the duplicate `run:` key that #978
repaired three hours later. Filtering to the default branch would have cleared
today's rows by luck — the phantoms happened to be elsewhere — while leaving the
defect. The test is whether a job ran.

SO THE BRANCH DECIDES WHAT IT MEANS, not whether to look. A run that never
started ON THE DEFAULT BRANCH is real news: the shipped workflow file cannot
start, so it is kept and reported. On any other branch it is a stale or broken
copy that says nothing about the tree, and the branch may not exist any more, so
it is dropped.

WHAT THE CONFIRMATION COSTS, MEASURED RATHER THAN GUESSED. One request per
SUSPECTED run, and a suspected run exists only where a commit carried a workflow
file that would not parse — one per broken file, not one per workflow. The push
that caused all of this carried three (#978 repaired a duplicate `run:` key in
three workflows), so the roster-health run that watches 126 workflows spends
three extra requests today. Manager traffic and the roster workflows share one
account budget, which is why this is stated.

THE SHAPE TEST IS A PROXY AND THE JOB COUNT IS THE MEASUREMENT. `never_started`
reads two things already in the run object — GitHub falls back to the file PATH
where a run's `name` would be, because it could not read the file's own `name:`,
and the run has zero elapsed time — which costs no request. That is an inference,
so a caller that can spend one request passes `job_count` and the inference is
CONFIRMED before anything is dropped. Silence about a frozen roster is the
expensive direction, so an unconfirmable run is kept rather than dropped.

DEFAULT_BRANCH is a constant here rather than fetched, and here rather than in
each caller, because one literal in the one module both scripts read cannot
disagree with itself.

WHAT THIS DELIBERATELY DOES NOT DECIDE. A run that DID start is kept whatever
branch it ran on, so a workflow_dispatch against a feature branch still counts as
a success — and in this repository those are real refreshes, dispatched to reach
sources a sandbox cannot (runs 35410869399 and 35453832897 of the municipal
roster, both 2026-09-19). Whether such a run should clear the staleness clock for
the SHIPPED roster is a fair question and a different one: it produced data on a
branch, not on main. Narrowing successes to the default branch would move several
workflows this change has not measured one by one, so the question is recorded
here rather than answered. It is adjacent to a limitation already on the record —
a refresh can report success while the builder skips a county and the shipped
file does not move, which is how #982 froze Illinois's municipal roster for
eleven days with nothing going red.

Run `python3 scripts/workflow_run_evidence.py --selftest` for the predicate's
cases, which are the runs measured above.
"""

import sys

DEFAULT_BRANCH = "main"


def never_started(run):
    """True when this run looks like one in which no job ever ran.

    An inference from two fields, not a measurement — see `job_count` on
    `evidence()`, which confirms it.
    """
    name = (run.get("name") or "").strip()
    path = (run.get("path") or "").strip()
    began = (run.get("run_started_at") or run.get("created_at") or "").strip()
    ended = (run.get("updated_at") or "").strip()
    # GitHub puts the file path where the workflow's own `name:` would go when it
    # could not read the file, and a run with no job takes no time.
    return bool(name) and name == path and bool(began) and began == ended


def evidence(runs, default_branch=DEFAULT_BRANCH, job_count=None):
    """`runs`, in the order given, minus the ones that say nothing about the refresh.

    `job_count(run)` returns that run's job count, or None where it cannot be
    read; without it the shape test stands alone.
    """
    kept = []
    for run in runs:
        if not never_started(run):
            kept.append(run)
            continue
        if (run.get("head_branch") or "") == default_branch:
            kept.append(run)          # the shipped file cannot start: that IS the news
            continue
        if job_count is not None:
            count = job_count(run)
            if count is None or count > 0:
                kept.append(run)      # unconfirmed, or it did start — keep it
                continue
        # Everything left is a stale copy of the file on another branch.
    return kept


def job_counter(api_get, repo):
    """A `job_count` for `evidence()` over a `api_get(path) -> dict` callable."""
    def count(run):
        try:
            data = api_get("/repos/%s/actions/runs/%s/jobs?per_page=1"
                           % (repo, run.get("id")))
            return int(data.get("total_count"))
        except Exception:             # noqa: BLE001 — unreadable means unknown, never zero
            return None
    return count


# Measured 2026-09-23 against the live API; see the module docstring.
_PHANTOM_OTHER_BRANCH = {
    "id": 35782165269, "name": ".github/workflows/update-mps-school-board-roster.yml",
    "path": ".github/workflows/update-mps-school-board-roster.yml",
    "event": "push", "head_branch": "claude/goat-counter-data-access-g5ycax",
    "conclusion": "failure", "run_started_at": "2026-09-22T20:43:45Z",
    "created_at": "2026-09-22T20:43:45Z", "updated_at": "2026-09-22T20:43:45Z",
}
_PHANTOM_ON_MAIN = {
    "id": 35166293478, "name": ".github/workflows/update-mps-school-board-roster.yml",
    "path": ".github/workflows/update-mps-school-board-roster.yml",
    "event": "push", "head_branch": "main", "conclusion": "failure",
    "run_started_at": "2026-09-17T00:22:30Z", "created_at": "2026-09-17T00:22:30Z",
    "updated_at": "2026-09-17T00:22:30Z",
}
_HEALTHY = {
    "id": 35648845084, "name": "Update MPS school board roster",
    "path": ".github/workflows/update-mps-school-board-roster.yml",
    "event": "schedule", "head_branch": "main", "conclusion": "success",
    "run_started_at": "2026-09-21T20:05:06Z", "created_at": "2026-09-21T20:05:06Z",
    "updated_at": "2026-09-21T20:05:33Z",
}
_DISPATCH_ON_BRANCH = {
    "id": 35453832897, "name": "Update municipal officials roster",
    "path": ".github/workflows/update-municipal-officials.yml",
    "event": "workflow_dispatch", "head_branch": "claude/il-backlog-plan-9o2ew4",
    "conclusion": "success", "run_started_at": "2026-09-19T16:05:23Z",
    "created_at": "2026-09-19T16:05:23Z", "updated_at": "2026-09-19T16:15:39Z",
}


def selftest():
    fails = []

    ran = []

    def check(what, got, want):
        ran.append(what)
        if got != want:
            fails.append("%s: got %r, wanted %r" % (what, got, want))

    check("phantom off main is never_started", never_started(_PHANTOM_OTHER_BRANCH), True)
    check("phantom on main is never_started", never_started(_PHANTOM_ON_MAIN), True)
    check("a real run is not", never_started(_HEALTHY), False)
    check("a branch dispatch is not", never_started(_DISPATCH_ON_BRANCH), False)
    check("no fields at all", never_started({}), False)
    # A run whose name matches its path but which took time did start.
    check("name matches path, time elapsed",
          never_started(dict(_PHANTOM_OTHER_BRANCH, updated_at="2026-09-22T20:44:59Z")),
          False)
    # A zero-length run that carries the workflow's own name did start and was
    # cancelled or skipped at once; it is not this shape.
    check("zero elapsed under the workflow's own name",
          never_started(dict(_HEALTHY, updated_at=_HEALTHY["run_started_at"])), False)

    newest_first = [_PHANTOM_OTHER_BRANCH, _HEALTHY, _PHANTOM_ON_MAIN]
    check("the phantom off main is dropped",
          [r["id"] for r in evidence(newest_first, job_count=lambda r: 0)],
          [_HEALTHY["id"], _PHANTOM_ON_MAIN["id"]])
    check("order is preserved",
          [r["id"] for r in evidence(newest_first, job_count=lambda r: 0)][0],
          _HEALTHY["id"])
    check("an unconfirmable run is kept, never dropped",
          [r["id"] for r in evidence(newest_first, job_count=lambda r: None)],
          [r["id"] for r in newest_first])
    check("a run the count says did start is kept",
          [r["id"] for r in evidence(newest_first, job_count=lambda r: 3)],
          [r["id"] for r in newest_first])
    check("with no counter the shape test stands alone",
          [r["id"] for r in evidence(newest_first)],
          [_HEALTHY["id"], _PHANTOM_ON_MAIN["id"]])
    check("a different default branch moves which phantom is kept",
          [r["id"] for r in evidence(newest_first, default_branch="trunk",
                                     job_count=lambda r: 0)],
          [_HEALTHY["id"]])
    check("nothing is dropped from an all-healthy list",
          [r["id"] for r in evidence([_HEALTHY, _DISPATCH_ON_BRANCH],
                                     job_count=lambda r: 0)],
          [_HEALTHY["id"], _DISPATCH_ON_BRANCH["id"]])
    check("an empty list stays empty", evidence([]), [])

    counted = []
    evidence(newest_first, job_count=lambda r: counted.append(r["id"]) or 0)
    check("only a suspected run costs a request", counted, [_PHANTOM_OTHER_BRANCH["id"]])

    if fails:
        for line in fails:
            print("workflow-run-evidence FAIL — " + line, file=sys.stderr)
        return 1
    print("workflow-run-evidence --selftest: OK — %d assertions over the four run "
          "shapes measured 2026-09-23" % len(ran))
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv[1:]:
        sys.exit(selftest())
    print(__doc__.strip())
