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

AND A SECOND QUESTION, ADDED 2026-09-27: DID THE RUN DO THE WORK? Six of these
workflows forgive a fetch that fails, so a run whose scrape died concludes
SUCCESS and rebuilt nothing. `verify_step` derives, from the workflow file, the
step whose running proves the work happened, and `run_did_work` reads whether it
ran. Measured across the six on 2026-09-27: 14 of 56 successful runs had not
rebuilt anything, and reading conclusions instead of that step put McHenry's
watchdog verdict at OK on four dates and Kendall's on five, nine in all, while
NEITHER county had ever been reached — every one in the dangerous direction. The
forgiven step's own conclusion cannot be the signal, because this API reports a
forgiven failure as `success`; the step gated on it is the one it leaves
unmasked, as `skipped`.

THE REMAINING LIMITATION IS NARROWER AND STILL OPEN. A refresh can report success
while the builder RUNS and skips a county, and the shipped file does not move —
which is how #982 froze Illinois's municipal roster for eleven days with nothing
going red. Nothing here sees that: the witness answers whether the builder ran,
never what it wrote. `check_roster_retention.py` is the gate that reads what a
builder wrote, and it reads the file rather than the run.

WHAT THIS DELIBERATELY DOES NOT DECIDE. A run that DID start is kept whatever
branch it ran on, so a workflow_dispatch against a feature branch still counts as
a success — and in this repository those are real refreshes, dispatched to reach
sources a sandbox cannot (runs 35410869399 and 35453832897 of the municipal
roster, both 2026-09-19). Whether such a run should clear the staleness clock for
the SHIPPED roster is a fair question and a different one: it produced data on a
branch, not on main. Narrowing successes to the default branch would move several
workflows this change has not measured one by one, so the question is recorded
here rather than answered. It is adjacent to the narrower limitation
recorded above, which is still open.

Run `python3 scripts/workflow_run_evidence.py --selftest` for the predicate's
cases, which are the runs measured above.
"""

import re
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


# --------------------------------------------------------------- did it do the work?

_STEP_NAME = re.compile(r"^(\s*)- name:\s*(.+?)\s*$")
_STEP_ID = re.compile(r"^\s*id:\s*(\S+)\s*$")
_FORGIVEN = re.compile(r"^\s*continue-on-error:\s*true\s*$")
_STEP_IF = re.compile(r"^(\s*)if:\s*(.*)$")
# A step's condition asserting that another step SUCCEEDED, in the two spellings
# this repository uses: GitHub's own `outcome`, and a script's exit code captured
# as a step output by a workflow that wants to branch on it.
_SUCCEEDED = re.compile(r"steps\.([A-Za-z0-9_-]+)\.(?:outcome\s*==\s*'success'"
                        r"|outputs\.[A-Za-z0-9_]+\s*==\s*'0')")
_FAILED = re.compile(r"steps\.([A-Za-z0-9_-]+)\.(?:outcome\s*==\s*'failure'"
                     r"|outputs\.[A-Za-z0-9_]+\s*!=\s*'0')")
_BLOCK_SCALAR = ("|", ">", "|-", ">-", "|+", ">+")


def workflow_steps(text):
    """`{name, id, forgiven, cond}` per step of a workflow file, in file order.

    Deliberately a line reader rather than a YAML parse: this module is stdlib
    only, it is imported by a step running inside one of these workflows, and
    every shape it has to read is a step key at a fixed indent. A folded `if: |`
    block is joined into one condition string, which `update-municipal-officials`
    needs — its condition runs 22 lines.
    """
    steps, cur, if_indent = [], None, None
    for raw in text.split("\n"):
        m = _STEP_NAME.match(raw)
        if m:
            if cur is not None:
                steps.append(cur)
            cur = {"name": m.group(2), "id": None, "forgiven": False, "cond": ""}
            if_indent = None
            continue
        if cur is None:
            continue
        if if_indent is not None:
            stripped = raw.strip()
            indent = len(raw) - len(raw.lstrip())
            if stripped and indent > if_indent:
                cur["cond"] = (cur["cond"] + " " + stripped).strip()
                continue
            if_indent = None
        m = _STEP_ID.match(raw)
        if m and cur["id"] is None:
            cur["id"] = m.group(1)
            continue
        if _FORGIVEN.match(raw):
            cur["forgiven"] = True
            continue
        m = _STEP_IF.match(raw)
        if m:
            cond = m.group(2).strip()
            cur["cond"] = "" if cond in _BLOCK_SCALAR else cond
            if_indent = len(m.group(1))
    if cur is not None:
        steps.append(cur)
    return steps


def verify_step(text):
    """The name of the step whose execution proves this workflow did its work.

    None where the workflow forgives nothing (its conclusion already means what
    it says) or where no step asserts a forgiven step SUCCEEDED, which is the
    honest answer for a watcher that never rebuilds anything.

    TWO RULES, AND THE NAIVE DERIVATION IS WRONG ON SIX OF SEVEN. "The first step
    whose `if:` reads another step's outcome" picks, on six of the seven
    workflows that forgive a step, the step that REPORTS THE FAILURE —
    `Report blocked source on the standing issue`, `Track a blocked or broken
    source`, watch-mason's `Open or update the tracking issue`. Reading any of
    those as the witness inverts the verdict exactly: every forgiven run would
    read as having done the work and every real one as not. So a condition must
    assert a forgiven step SUCCEEDED, and a condition that also asserts anything
    FAILED is a reporter rather than a witness.

    On this tree those two rules are redundant with each other — either alone
    gives the right answer on all seven — because the reporters here are gated on
    failure ALONE. The second is still load-bearing for a shape the tree does
    contain: `update-municipal-officials`'s `Track a township build refusal` is
    `steps.scrape_cook.outcome == 'success' && steps.build_townships.outcome ==
    'failure'`, which the first rule accepts and the second rejects. It is masked
    only by that step sitting after the rebuild in file order, which is not a
    property worth depending on.

    THE FIRST MATCH, NOT ANY MATCH. Several later steps are gated the same way
    and are weaker witnesses: `Open or update pull request` also requires that
    the data CHANGED, so a run that refreshed a roster to the same content would
    read as not having done the work.

    A name that is not unique among the workflow's steps returns None, because
    the jobs API is keyed by step name and two steps sharing one would make the
    lookup ambiguous. No workflow here has that shape today.
    """
    steps = workflow_steps(text)
    forgiven = set(s["id"] for s in steps if s["forgiven"] and s["id"])
    if not forgiven:
        return None
    for step in steps:
        cond = step["cond"]
        if not cond or _FAILED.search(cond):
            continue
        if not any(g in forgiven for g in _SUCCEEDED.findall(cond)):
            continue
        if sum(1 for other in steps if other["name"] == step["name"]) != 1:
            return None
        return step["name"]
    return None


def run_did_work(jobs_payload, step):
    """True where `step` RAN in this run, read from the jobs API's step list.

    THE FORGIVEN STEP'S OWN CONCLUSION CANNOT BE THE SIGNAL. A
    `continue-on-error` step that failed is reported `conclusion: "success"` by
    this API — measured on `update-mchenry-county-board-roster` run 8
    (2026-08-28), whose `if: steps.scrape.outcome == 'failure'` step fired, so
    the failure is knowable only from the conditional step. The step gated on it
    is the one the API leaves unmasked, as `skipped`.

    A missing step reads False: a run whose job list does not carry the witness
    at all did not run it. That is the same direction as `skipped` and the
    opposite of the `never_started` rule above, where an unreadable run is KEPT —
    there the expensive direction is silence about a frozen roster, and here a
    False only ever makes the report look FURTHER from fresh, never closer.
    """
    for job in jobs_payload.get("jobs") or []:
        for entry in job.get("steps") or []:
            if entry.get("name") == step:
                return entry.get("conclusion") == "success"
    return False


def failed_step(jobs_payload):
    """The name of the step whose FAILURE stopped this run, or None.

    The first step concluding `failure`, in the order the API returns the job's
    steps. Its one caller asks a narrow question -- is this red run the one a
    declining scraper explains, or is it something else -- so `cancelled` and
    `timed_out` are deliberately NOT read as a failure here: a scrape step the
    runner killed is a different event from a scrape step that declined, and
    reading them alike would let one entry cover the other.

    A FORGIVEN STEP'S FAILURE IS MASKED AS `success` BY THIS API, which
    `run_did_work` above measures and records. So this can only ever name a step
    whose failure actually stopped the job -- which is the same thing as saying it
    cannot name a step some workflow chose to forgive, and is why the caller's
    verdict does not depend on a run conclusion.

    None where nothing failed, where the payload could not be read, or where the
    job list carries no steps. Unreadable is unknown, and the caller treats
    unknown as "not explained" rather than as "expected".
    """
    for job in jobs_payload.get("jobs") or []:
        for entry in job.get("steps") or []:
            if entry.get("conclusion") == "failure":
                return entry.get("name")
    return None

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

# The forgive-then-skip shape, trimmed from update-mchenry-county-board-roster.yml
# with its step names, ids, `continue-on-error` and every `if:` verbatim. The
# reporter sits BEFORE the rebuild there, which is what makes the naive
# derivation pick it.
_WF_FORGIVE_THEN_SKIP = """
name: Update McHenry County Board roster
jobs:
  refresh:
    steps:
      - name: Scrape McHenry County Board member roster
        id: scrape
        continue-on-error: true
        run: python3 scripts/mchenry_county_board_scraper.py
      - name: Report blocked source on the standing issue
        if: steps.scrape.outcome == 'failure'
        run: gh issue comment
      - name: Rebuild roster data file
        if: steps.scrape.outcome == 'success'
        run: python3 scripts/build_mchenry_county_board.py
      - name: Open or update pull request
        if: steps.scrape.outcome == 'success' && steps.diff.outputs.changed == 'true'
        run: gh pr create
"""

# watch-mason-roster-source.yml's shape: a watcher forgives its fetch and gates
# only an issue on the failure. There is no step whose running proves a refresh,
# because it refreshes nothing.
_WF_WATCHER = """
name: Watch Mason County Board roster source
jobs:
  watch:
    steps:
      - name: Check the published directory
        id: watch
        continue-on-error: true
        run: python3 scripts/mason_roster_watch.py
      - name: Open or update the tracking issue
        if: steps.watch.outputs.code != '0'
        run: gh issue comment
"""

# update-municipal-officials.yml's mixed condition, which asserts a forgiven step
# succeeded AND another failed. Placed FIRST here, which the real file does not
# do, so the guard is tested rather than masked by file order.
_WF_MIXED_FIRST = """
jobs:
  refresh:
    steps:
      - name: Scrape the Cook County Clerk directory of elected officials
        id: scrape_cook
        continue-on-error: true
        run: python3 scripts/cook_municipal_officials_scraper.py
      - name: Track a township build refusal
        if: steps.scrape_cook.outcome == 'success' && steps.build_townships.outcome == 'failure'
        run: gh issue comment
      - name: Rebuild roster data file
        if: steps.scrape_cook.outcome == 'success'
        run: python3 scripts/build_municipal_officials_roster.py
"""

# A folded condition, which update-municipal-officials.yml needs: its own runs 22
# lines. Two steps share a name here, which makes the jobs-API lookup ambiguous.
_WF_FOLDED = """
jobs:
  refresh:
    steps:
      - name: Scrape one
        id: one
        continue-on-error: true
        run: true
      - name: Track a blocked or broken source
        if: |
          steps.one.outcome == 'failure' ||
          steps.two.outcome == 'failure'
        run: true
      - name: Rebuild roster data file
        if: steps.one.outcome == 'success'
        run: true
"""

_WF_DUPLICATE_NAMES = _WF_FOLDED.replace(
    "      - name: Scrape one\n", "      - name: Rebuild roster data file\n")

# Nothing forgiven: the run's own conclusion already means what it says.
_WF_NO_FORGIVENESS = """
jobs:
  refresh:
    steps:
      - name: Scrape
        id: scrape
        run: true
      - name: Rebuild roster data file
        run: true
"""

# update-mchenry-county-board-roster run 8, 2026-08-28: the scrape genuinely
# failed and the jobs API reports it `success` because it is forgiven, while the
# step gated on it reads `skipped`. Measured against the live API 2026-09-27.
_JOBS_RUN_8 = {"jobs": [{"steps": [
    {"name": "Scrape McHenry County Board member roster", "conclusion": "success"},
    {"name": "Report blocked source on the standing issue", "conclusion": "success"},
    {"name": "Rebuild roster data file", "conclusion": "skipped"},
]}]}
# run 11, 2026-09-17: the same workflow, the scrape reached the county.
_JOBS_RUN_11 = {"jobs": [{"steps": [
    {"name": "Scrape McHenry County Board member roster", "conclusion": "success"},
    {"name": "Report blocked source on the standing issue", "conclusion": "skipped"},
    {"name": "Rebuild roster data file", "conclusion": "success"},
]}]}
# A reporter written `!= 'success'` rather than `== 'failure'`. Neither spelling
# is a witness, and only the polarity rule catches this one — the failure regex
# matches `== 'failure'` and `!= '0'` and not this. No workflow here writes it;
# it is the idiom a future one is most likely to reach for.
_WF_NOT_SUCCESS_REPORTER = """
jobs:
  refresh:
    steps:
      - name: Scrape
        id: scrape
        continue-on-error: true
        run: true
      - name: Report blocked source on the standing issue
        if: steps.scrape.outcome != 'success'
        run: true
      - name: Rebuild roster data file
        if: steps.scrape.outcome == 'success'
        run: true
"""

# The WITNESS carries the folded condition here. In _WF_FOLDED the reporter does,
# and dropping the continuation makes the reporter merely look conditionless —
# which excludes it for a second reason and hides the defect. Losing the
# continuation here loses the witness instead, which is what needs to fail.
_WF_FOLDED_WITNESS = """
jobs:
  refresh:
    steps:
      - name: Scrape
        id: scrape
        continue-on-error: true
        run: true
      - name: Rebuild roster data file
        if: |
          steps.scrape.outcome == 'success' &&
          github.ref == 'refs/heads/main'
        run: true
"""

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

    check("the forgive-then-skip shape yields its rebuild",
          verify_step(_WF_FORGIVE_THEN_SKIP), "Rebuild roster data file")
    check("a watcher yields nothing rather than its issue step",
          verify_step(_WF_WATCHER), None)
    check("a mixed success-and-failure condition is not the witness",
          verify_step(_WF_MIXED_FIRST), "Rebuild roster data file")
    check("a folded if: block is read whole",
          verify_step(_WF_FOLDED), "Rebuild roster data file")
    check("two steps sharing the witness name is refused, not guessed",
          verify_step(_WF_DUPLICATE_NAMES), None)
    check("a workflow that forgives nothing needs no witness",
          verify_step(_WF_NO_FORGIVENESS), None)
    check("no steps at all", verify_step(""), None)
    check("a reporter written != 'success' is not the witness either",
          verify_step(_WF_NOT_SUCCESS_REPORTER), "Rebuild roster data file")
    check("a folded condition on the witness itself is read whole",
          verify_step(_WF_FOLDED_WITNESS), "Rebuild roster data file")
    # The trap: the reporter comes FIRST in the real file, so a derivation that
    # took any step referencing the scrape would read every forgiven run as
    # having done the work.
    check("the reporter is never picked even though it comes first",
          verify_step(_WF_FORGIVE_THEN_SKIP) != "Report blocked source on the standing issue",
          True)

    check("run 8 skipped its rebuild",
          run_did_work(_JOBS_RUN_8, "Rebuild roster data file"), False)
    check("run 11 ran its rebuild",
          run_did_work(_JOBS_RUN_11, "Rebuild roster data file"), True)
    # The masked step: asking the forgiven step itself answers success on the run
    # whose scrape failed, which is why it can never be the signal.
    check("the forgiven step reads success on the run that failed",
          run_did_work(_JOBS_RUN_8, "Scrape McHenry County Board member roster"), True)
    check("a witness the run does not carry reads False",
          run_did_work(_JOBS_RUN_11, "Rebuild the Court of Appeals roster"), False)
    check("an empty payload reads False", run_did_work({}, "Rebuild roster data file"), False)
    counted = []
    evidence(newest_first, job_count=lambda r: counted.append(r["id"]) or 0)
    check("only a suspected run costs a request", counted, [_PHANTOM_OTHER_BRANCH["id"]])

    # WHICH STEP'S FAILURE STOPPED THE RUN, from the real jobs payload of
    # update-county-clerk-roster run 12 (36256724325, 2026-09-26): the ISBE
    # scrape declined, every later step skipped. Trimmed to name, conclusion and
    # number, which is all `failed_step` reads.
    clerk_jobs = {"jobs": [{"name": "update-roster", "conclusion": "failure", "steps": [
        {"name": "Set up job", "conclusion": "success", "number": 1},
        {"name": "Run actions/checkout@v4", "conclusion": "success", "number": 2},
        {"name": "Run actions/setup-python@v5", "conclusion": "success", "number": 3},
        {"name": "Install scraper dependencies", "conclusion": "success", "number": 4},
        {"name": "Install Chromium for the browser rung", "conclusion": "success",
         "number": 5},
        {"name": "Scrape the ISBE election-authority directory",
         "conclusion": "failure", "number": 6},
        {"name": "Rebuild roster data file", "conclusion": "skipped", "number": 7},
        {"name": "Validate app + data files", "conclusion": "skipped", "number": 9},
        {"name": "Complete job", "conclusion": "success", "number": 23},
    ]}]}
    check("the failing step is named, not the job",
          failed_step(clerk_jobs), "Scrape the ISBE election-authority directory")
    check("a run with nothing failed names no step",
          failed_step({"jobs": [{"steps": [
              {"name": "Scrape", "conclusion": "success"},
              {"name": "Rebuild", "conclusion": "success"}]}]}), None)
    # A CANCELLED OR TIMED-OUT STEP IS NOT A FAILURE HERE, deliberately: the
    # caller uses this to decide whether a declining scraper explains a red run,
    # and a step the runner killed is a different event.
    check("a cancelled step is not read as the failure",
          failed_step({"jobs": [{"steps": [
              {"name": "Scrape", "conclusion": "cancelled"}]}]}), None)
    check("a timed-out step is not read as the failure",
          failed_step({"jobs": [{"steps": [
              {"name": "Scrape", "conclusion": "timed_out"}]}]}), None)
    check("an unreadable payload names no step", failed_step({}), None)
    check("a job with no step list names no step",
          failed_step({"jobs": [{"name": "update-roster"}]}), None)

    if fails:
        for line in fails:
            print("workflow-run-evidence FAIL — " + line, file=sys.stderr)
        return 1
    print("workflow-run-evidence --selftest: OK — %d assertions: the four run "
          "shapes measured 2026-09-23, the witness derivation measured "
          "2026-09-27 and the failing-step reader against run 36256724325's own "
          "payload" % len(ran))
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv[1:]:
        sys.exit(selftest())
    print(__doc__.strip())
