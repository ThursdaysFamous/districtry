#!/usr/bin/env python3
"""
Watchdog for the weekly roster refreshes: which ones are FAILING, and which have
gone too long without a successful run.

THE GAP THIS CLOSES. Every roster builder refuses to write when too few records
resolve — that is deliberate and good, and about a dozen counties deliberately
floor at their exact board size so that ANY vacancy stops the write rather than
shipping a short roster. What none of them does is tell anyone. A builder that
exits non-zero fails its workflow step, the run goes red, and then: no pull
request opens (there is no data change to open one with), no issue is filed, and
the shipped file goes on naming whoever it named last week. The only signal is a
red run in the Actions tab, which nobody watches. So the counties that handle a
vacancy most conservatively are exactly the ones whose vacancy is least likely
to be NOTICED. This is the thing that looks.

WHY A WATCHDOG RATHER THAN A HANDLER IN EACH WORKFLOW. There are 50-odd refresh
workflows and one is added with roughly every county. A failure-reporting step
pasted into each would be fifty copies of the same shell that every future
workflow must remember to carry. This DISCOVERS the workflows from
.github/workflows/ instead, so a new county is watched the day it ships with
nothing to update — the same argument validate_card_links.py makes for
extracting its URL surface rather than keeping a manifest of it.

WHAT IT REPORTS, AND WHY STALENESS IS THE USEFUL HALF. A single red run is
often nothing: a county's site was down for an hour. A roster that has not
refreshed SUCCESSFULLY in a month is a roster frozen a month ago, and that is
the number a human can act on. So every workflow is measured against its own
cron cadence (weekly crons expect a run every 7 days, monthly every 31) and
reported as:

    FAILING  — its most recent completed run failed, and nothing has changed since
    UNPROVEN — it failed, but the code it runs has been EDITED since that run,
               so the red predates the fix and the next run is the first test
    STALE    — no successful run within roughly two of its own intervals
    UNMEASURED— it forgives a fetch, and no run inside the history read actually
               rebuilt anything, so how long since it refreshed is a floor
    SILENT   — old enough to have run, and never has
    DISABLED — switched off, so it is not refreshing anything
    NEW      — added too recently for its cron to have fired (not a problem)
    ON-DEMAND— it declares no schedule at all, so it has no cadence to be late
               against; watched for a red run and never for staleness
    OK       — succeeded within its cadence

FAILING and STALE overlap constantly and that is intentional: failing once is a
blip, failing for three weeks is a frozen roster, and the report says which.

A RED RUN THAT PREDATES ITS OWN FIX IS NOT A LIVE FAILURE, and McHenry is why
this distinction exists. Its 13 August run failed; ninety-one minutes later a
commit fixed exactly that failure, and its weekly cron will not come round again
until the 20th. For six days the report said FAILING about a bug that no longer
existed, and someone acted on it — read the run, diagnosed the shape, and went
looking for a fix already in the tree. So each workflow's latest run is compared
against the last commit touching the workflow file or any script it invokes: if
the code moved after the run, the verdict is UNPROVEN rather than FAILING, which
says the thing a reader needs — do not chase this, but do not forget it either.
It costs a `git log` per workflow and needs history, so the job checks out with
fetch-depth 0.

A WORKFLOW TOO YOUNG TO HAVE RUN IS NOT SILENT, and the first live run of this
script is what taught it so: Clark, Edgar and Mercer shipped that same afternoon
and their weekly crons had not come round once, so all three read SILENT on a
report whose whole point is to be actionable. The workflows API carries each
workflow's `created_at`, so anything younger than one of its own intervals is
reported as NEW and never as a problem. It also carries `state`, which is worth
watching for its own reason: GitHub disables scheduled workflows after 60 days
of repository inactivity, and a disabled workflow is not failing, not stale, and
not running.

A GREEN RUN IS NOT EVIDENCE THE JOB DID ITS WORK, and until 2026-09-27 this file
read one anyway. Six of the watched workflows wrap their scrape in
`continue-on-error`, so a run whose fetch died concludes SUCCESS having rebuilt
nothing, and the staleness clock here read run conclusions. Measured that day
against this repository's own history: 14 of 56 successful runs across those six
had not rebuilt anything, and replaying this function over McHenry's and
Kendall's full histories flips the verdict on FOUR dates and FIVE respectively —
nine in all, every one of them OK where the honest answer is STALE or
UNMEASURED, and in both cases during a stretch when NEITHER county had ever been
reached at all. So the clock now reads the newest run in which the workflow's own
rebuild step RAN.

THOSE FIGURES ARE THE REPLAY'S, NOT ARITHMETIC. A first pass counted five and six
by comparing ages by hand, which double-counted dates whose latest run had FAILED
and therefore read FAILING under both readings — no flip. The replay runs
`classify` itself over each prefix of the real history, which is the only reading
that cannot disagree with the code.
`workflow_run_evidence.verify_step` derives that step from the workflow file and
records why the obvious derivation is wrong on six of seven; `run_did_work` reads
it out of the jobs API, where a forgiven step's own failure is MASKED as
`success` and only the step gated on it shows `skipped`.

No verdict on this tree is wrong today — DeKalb's clock reads 8 days against a
conclusion-based 1, and both are inside its limit — so this change removes a
blind spot rather than correcting a live row. It costs one request per successful
run examined, for those six workflows only, and stops at the first verified one.

A WORKFLOW WITH NO SCHEDULE CANNOT BE STALE, and verify-google-api-access.yml is
why this verdict exists. It is a MANUAL diagnostic — `on: workflow_dispatch` and
nothing else, run by hand after rotating the Google key — and `cadence_days`
returns None for a file with no cron, which the staleness clock then read as the
7-day default: `limit = (cadence or 7) * 2 + 2`. So it went STALE 16 days after
its last hand-run, held the tracking issue open on a row nobody could clear
except by dispatching a diagnostic for no reason, and that is exactly the
wallpaper this file's own closing step warns about — an issue that never closes
is one the next real failure lands on unread. A cron-less workflow is reported
ON-DEMAND instead: still FAILING if its latest run failed, because a dispatch
that errors is a real credential problem, and never stale, because there is no
schedule to be late for. The test is the workflow's own trigger set rather than a
name on a list, so the next manual diagnostic is classified right on the day it
ships.

NO EXPECTED-FAILURE LIST, AND THAT IS A MEASUREMENT NOT AN OVERSIGHT. The two
counties known to block every automated client — Kendall and McHenry — do NOT
red their runs: their scrape step carries continue-on-error and feeds a standing
issue, so those workflows are green by design and this watchdog is silent about
them. Nothing else is currently expected to fail. If something ever is, it earns
an entry here the way validate_sources.py's `blocked` flag and
validate_card_links.py's EXPECTED_UNREACHABLE did — by being measured first, and
with the same inversion, so that RECOVERING becomes the reportable event.

Usage:
    python3 scripts/check_roster_workflow_health.py                  # needs GH_TOKEN
    python3 scripts/check_roster_workflow_health.py --report r.md --status-file s.txt
    python3 scripts/check_roster_workflow_health.py --list           # offline: what it watches
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

# One reader for "which runs are evidence about the refresh"; fleet_status.py
# asks the same module the same question.
import workflow_run_evidence

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOW_DIR = os.path.join(REPO_ROOT, ".github", "workflows")
API = "https://api.github.com"

# Workflows that are not data refreshes. Everything else in the directory is
# watched, which is what keeps a new county from being forgotten.
NOT_A_REFRESH = {
    "smoke-test.yml", "deploy-pages.yml", "validate-sources.yml",
    "engine-parity.yml", "fleet-status.yml", "release-engine.yml",
    "create-engine-tag.yml", "roster-health.yml",
}

CRON_RE = re.compile(r"^\s*-\s*cron:\s*[\"']([^\"']+)[\"']", re.M)
NAME_RE = re.compile(r"^name:\s*(.+)$", re.M)
# Only scripts the workflow actually RUNS. The `python3 ` prefix is what keeps
# this from matching script names mentioned in prose — several workflows name a
# builder inside the body of the issue they file, which is not code they run.
RUNS_RE = re.compile(r"python3\s+(scripts/[\w./-]+\.py)")


def cadence_days(cron):
    """Roughly how often this cron fires, in days.

    Only the shapes this repo actually uses are recognised: a weekday field
    naming one day (weekly), a day-of-month field naming one day (monthly), and
    everything else treated as daily. A wrong guess here only moves the
    staleness threshold, never the FAILING verdict.
    """
    if not cron:
        return None
    parts = cron.split()
    if len(parts) != 5:
        return 7
    dom, dow = parts[2], parts[4]
    if dom != "*":
        return 31
    if dow != "*":
        return 7
    return 1


# How many successful runs to ask about before reporting the age as a floor. One
# request each, so this bounds the cost; six workflows have a witness and the
# newest verified run has been the 1st or 2nd of them every time it was measured.
WITNESS_RUN_LIMIT = 8

# Worst first. A verdict missing here raises on sort rather than ordering
# silently, which the selftest holds against everything classify can return.
VERDICT_ORDER = {"FAILING": 0, "DISABLED": 1, "STALE": 2, "SILENT": 3,
                 "UNMEASURED": 4, "UNPROVEN": 5, "NEW": 6, "ON-DEMAND": 7, "OK": 8}

def discover():
    """Refresh workflows on disk: (filename, name, cadence, scripts, witness).

    `witness` is the step whose running proves the workflow did its work, or None
    where its conclusion already means what it says. Derived from the file, so it
    follows a workflow that is edited with nothing here to update.
    """
    out = []
    for fn in sorted(os.listdir(WORKFLOW_DIR)):
        if not fn.endswith((".yml", ".yaml")) or fn in NOT_A_REFRESH:
            continue
        path = os.path.join(WORKFLOW_DIR, fn)
        with open(path, encoding="utf-8") as f:
            src = f.read()
        name = NAME_RE.search(src)
        crons = CRON_RE.findall(src)
        out.append((fn, name.group(1).strip() if name else fn,
                    cadence_days(crons[0] if crons else None),
                    sorted(set(RUNS_RE.findall(src))),
                    workflow_run_evidence.verify_step(src)))
    return out


def own_scripts(watched):
    """Per workflow, the scripts that belong to IT rather than to everyone.

    A script run by many workflows is a shared GATE, not this county's logic:
    `validate_index.py` is invoked by 54 of these, so counting it would mark
    every workflow UNPROVEN the moment anyone touched it — turning the whole
    check off in one commit, which is precisely the failure mode this file
    exists to catch. Only scripts unique to a single workflow count.
    """
    uses = {}
    for row in watched:
        for sc in row[3]:
            uses[sc] = uses.get(sc, 0) + 1
    return {row[0]: [sc for sc in row[3] if uses.get(sc) == 1] for row in watched}


def code_changed_at(workflow_file, scripts):
    """When the workflow file or any script it runs was last committed.

    Returns None when git cannot answer — a shallow checkout, or a path that
    does not exist — in which case the caller simply does not apply the
    UNPROVEN downgrade rather than guessing either way.
    """
    paths = [os.path.join(".github", "workflows", workflow_file)] + list(scripts)
    paths = [p for p in paths if os.path.exists(os.path.join(REPO_ROOT, p))]
    if not paths:
        return None
    try:
        proc = subprocess.run(
            ["git", "log", "-1", "--format=%cI", "--"] + paths,
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    out = (proc.stdout or "").strip()
    if proc.returncode != 0 or not out:
        return None
    try:
        return parse_ts(out)
    except ValueError:
        return None


def api_get(path, token):
    req = urllib.request.Request(API + path, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + token,
        "User-Agent": "districtry-roster-health",
    })
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.load(resp)


def parse_ts(s):
    """GitHub timestamps, which are not one shape: run timestamps come back as
    2026-08-18T20:16:54Z and the workflows listing as 2026-08-01T14:41:24.000Z."""
    s = s.strip().replace("Z", "+00:00")
    return datetime.datetime.fromisoformat(s).astimezone(datetime.timezone.utc)


def classify(runs, cadence, now, created=None, state=None, code_at=None,
             witness=None, verified_at=None, floor_age=None):
    """(verdict, detail) for one workflow's recent runs, newest first.

    `witness` names the step whose running proves this workflow did its work, and
    `verified_at` is the newest successful run in which that step RAN. Where a
    witness exists the staleness clock reads THAT rather than the run conclusion,
    because a forgiven run concludes success having refreshed nothing —
    `workflow_run_evidence.verify_step` derives the step and says why.

    Where no verified run was found, `floor_age` is how long ago the OLDEST
    successful run examined started — so the true age is at least that. A floor
    is not automatically an absence of measurement: eight weekly runs that
    rebuilt nothing prove about eight weeks of not refreshing, which is STALE on
    the evidence. Only a floor still INSIDE the cadence limit leaves the question
    open, and that is the one reported UNMEASURED, which keeps this file's
    standing posture that an unjudgeable workflow is not called a failure.
    """
    if state and state != "active":
        return ("DISABLED", "workflow state is %r — it is not running at all" % state)

    young = created is not None and (now - created).days <= (cadence or 7)
    completed = [r for r in runs if r.get("status") == "completed"]
    if not completed:
        if young:
            return ("NEW", "added %d day(s) ago; its cron has not come round yet"
                    % (now - created).days)
        if cadence is None:
            return ("ON-DEMAND", "no schedule — run by hand; never dispatched")
        return ("SILENT", "no completed run on record")

    latest = completed[0]
    succeeded = [r for r in completed if r.get("conclusion") == "success"]
    last_ok = parse_ts(succeeded[0]["created_at"]) if succeeded else None
    # A run that was forgiven its fetch concludes success and refreshed nothing,
    # so where the witness can be read it is the clock. Measured 2026-09-27:
    # McHenry read OK on five dates and Kendall on six while neither county had
    # ever been reached, every one of those a verdict this reading flips.
    if witness is not None:
        last_ok = verified_at
    age = (now - last_ok).days if last_ok else None
    did = "" if witness is None else " (a run whose `%s` step ran)" % witness

    # Cancelled and skipped runs are neither a failure nor a refresh; they only
    # matter through the staleness clock, which they do not stop.
    failing = latest.get("conclusion") not in ("success", "cancelled", "skipped")
    limit = (cadence or 7) * 2 + 2
    stale = age is None or age > limit

    if failing:
        when = parse_ts(latest["created_at"])
        detail = "latest run %s on %s; last success%s %s" % (
            latest.get("conclusion"), when.date().isoformat(), did,
            "never" if age is None else "%d days ago" % age)
        # The red predates its own fix: the code has been edited since it ran,
        # so nothing has yet tested whether the failure survives.
        if code_at is not None and code_at > when:
            return ("UNPROVEN", detail + "; but its code changed on %s, after "
                    "that run — the next scheduled run is the first to test it"
                    % code_at.date().isoformat())
        return ("FAILING", detail)
    # No cron at all: there is no cadence to be late against, so the staleness
    # clock above (which defaults a cron-less file to 7 days) says nothing.
    if cadence is None:
        return ("ON-DEMAND", "no schedule — run by hand; last success%s %s"
                % (did, "never" if age is None else "%d days ago" % age))
    if stale and young:
        return ("NEW", "added %d day(s) ago; not enough history to judge"
                % (now - created).days)
    if stale:
        if witness is not None and verified_at is None:
            went_green = ("has never succeeded" if not succeeded else
                          "last went green %d days ago"
                          % (now - parse_ts(succeeded[0]["created_at"])).days)
            if floor_age is not None and floor_age > limit:
                return ("STALE", "it %s, and none of the %d successful run(s) "
                        "examined ran its `%s` step, so it has refreshed nothing "
                        "for at least %d days (expected within ~%d)"
                        % (went_green, len(succeeded), witness, floor_age, limit))
            return ("UNMEASURED", "it %s, but no run examined ran its `%s` step "
                    "and the history read does not reach back far enough to say "
                    "how long — read the runs" % (went_green, witness))
        return ("STALE", "last success%s %s (expected within ~%d days)"
                % (did, "never" if age is None else "%d days ago" % age, limit))
    return ("OK", "last success%s %d days ago" % (did, age))



def selftest():
    """`classify`'s verdicts, offline, against fixtures taken from real runs.

    This file is a workflow's own script and CI has never run it, so until
    2026-09-27 its verdict logic shipped with nothing testing it — which is the
    same shape as the defect this gate exists to catch, one level up. The witness
    cases are McHenry's and Kendall's own histories, replayed: both ran for weeks
    concluding success while rebuilding nothing.
    """
    fails, ran = [], []

    def check(what, got, want):
        ran.append(what)
        if got != want:
            fails.append("%s: got %r, wanted %r" % (what, got, want))

    now = datetime.datetime(2026, 9, 27, 4, 0, tzinfo=datetime.timezone.utc)

    def run(days_ago, conclusion="success"):
        when = now - datetime.timedelta(days=days_ago)
        return {"status": "completed", "conclusion": conclusion,
                "created_at": when.strftime("%Y-%m-%dT%H:%M:%SZ"), "html_url": "u"}

    def ago(days):
        return now - datetime.timedelta(days=days)

    weekly = [run(2), run(9), run(16), run(23), run(30), run(37), run(44), run(58)]

    # Without a witness nothing about this file's existing behaviour moves.
    check("no witness, fresh", classify(weekly, 7, now)[0], "OK")
    check("no witness, stale", classify([run(40)], 7, now)[0], "STALE")
    check("no witness, failing", classify([run(1, "failure")] + weekly, 7, now)[0], "FAILING")
    check("no witness, cancelled is not a failure",
          classify([run(1, "cancelled")] + weekly, 7, now)[0], "OK")

    # With one, the clock is the verified run rather than the green one.
    check("a verified run inside the cadence is OK",
          classify(weekly, 7, now, witness="Rebuild", verified_at=ago(2))[0], "OK")
    check("the verified run's age is what the detail states",
          "2 days ago" in classify(weekly, 7, now, witness="Rebuild",
                                   verified_at=ago(2))[1], True)
    check("a verified run outside the cadence is STALE",
          classify(weekly, 7, now, witness="Rebuild", verified_at=ago(40))[0], "STALE")
    # The McHenry/Kendall shape: green every week, rebuilt nothing for weeks.
    check("green weekly, nothing rebuilt for 58 days, is STALE on the floor",
          classify(weekly, 7, now, witness="Rebuild", verified_at=None,
                   floor_age=58)[0], "STALE")
    check("that STALE says it refreshed nothing rather than that it went red",
          "refreshed nothing for at least 58 days" in classify(
              weekly, 7, now, witness="Rebuild", verified_at=None, floor_age=58)[1], True)
    # A floor still inside the cadence settles nothing, and is not called stale.
    check("a floor inside the cadence is UNMEASURED, not STALE",
          classify(weekly[:2], 7, now, witness="Rebuild", verified_at=None,
                   floor_age=9)[0], "UNMEASURED")
    check("UNMEASURED says the history does not reach back far enough",
          "does not reach back far enough" in classify(
              weekly[:2], 7, now, witness="Rebuild", verified_at=None,
              floor_age=9)[1], True)
    # No successful run at all read no differently for having a witness.
    check("a workflow that has never succeeded is not UNMEASURED",
          classify([run(40, "failure")], 7, now, witness="Rebuild")[0], "FAILING")
    # The verdicts this file already refuses to call a problem are unchanged.
    check("disabled outranks everything",
          classify(weekly, 7, now, state="disabled_manually")[0], "DISABLED")
    check("a cron-less workflow is never stale",
          classify([run(90)], None, now, witness="Rebuild", verified_at=ago(90))[0],
          "ON-DEMAND")
    check("every verdict classify can return is orderable",
          sorted({"FAILING", "DISABLED", "STALE", "SILENT", "UNMEASURED",
                  "UNPROVEN", "NEW", "ON-DEMAND", "OK"} - set(VERDICT_ORDER)), [])

    # The witness derivation is workflow_run_evidence's and tested there; what
    # this asserts is that THIS file's watched set still finds the six, because a
    # discover() that stopped returning them would empty the whole change.
    witnessed = [row[0] for row in discover() if row[4] is not None]
    check("the watched set still yields the workflows that forgive a fetch",
          len(witnessed) >= 6, True)

    if fails:
        for line in fails:
            print("check-roster-health FAIL — " + line, file=sys.stderr)
        return 1
    print("check-roster-health --selftest: OK — %d assertions, %d watched workflow(s) "
          "carrying a witness step" % (len(ran), len(witnessed)))
    return 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY",
                                                     "ThursdaysFamous/DistrictExplorer-CHI"))
    ap.add_argument("--report")
    ap.add_argument("--status-file")
    ap.add_argument("--list", action="store_true",
                    help="print the watched workflows and exit (no network)")
    args = ap.parse_args()

    watched = discover()
    if args.list:
        for fn, name, cad, scripts, witness in watched:
            print("%-46s every ~%s days   %s%s" % (
                fn, cad, name,
                "" if witness is None else "   [witness: %s]" % witness))
        print("\n%d refresh workflow(s) watched" % len(watched))
        return

    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("check-roster-health: no GH_TOKEN/GITHUB_TOKEN — cannot read run "
              "history. Use --list for the offline inventory.", file=sys.stderr)
        sys.exit(2)

    now = datetime.datetime.now(datetime.timezone.utc)

    # One listing call carries created_at and state for every workflow, which is
    # what separates "never ran" from "added yesterday" and catches a workflow
    # GitHub has switched off. Cheaper and more truthful than reading the file's
    # git history, which a shallow CI checkout would not have anyway.
    meta = {}
    try:
        listing = api_get("/repos/%s/actions/workflows?per_page=100" % args.repo, token)
        for wf in listing.get("workflows") or []:
            meta[os.path.basename(wf.get("path") or "")] = wf
    except Exception as exc:                                      # noqa: BLE001
        print("check-roster-health: could not list workflows (%s) — ages and "
              "disabled state unavailable this run" % exc, file=sys.stderr)

    own = own_scripts(watched)
    rows, unreadable = [], []
    for fn, name, cad, scripts, witness in watched:
        wf = meta.get(fn) or {}
        created = parse_ts(wf["created_at"]) if wf.get("created_at") else None
        state = wf.get("state")
        try:
            data = api_get("/repos/%s/actions/workflows/%s/runs?per_page=20"
                           % (args.repo, fn), token)
            # A run GitHub recorded for a workflow file it could not START is not
            # evidence about the refresh: no job ran and nothing was scraped. Two
            # rows of this report named exactly that on 2026-09-23. One reader
            # answers that question for this script and fleet_status.py alike.
            runs = workflow_run_evidence.evidence(
                data.get("workflow_runs") or [],
                job_count=workflow_run_evidence.job_counter(
                    lambda path: api_get(path, token), args.repo))
        except urllib.error.HTTPError as exc:
            unreadable.append((fn, name, "HTTP %s" % exc.code))
            continue
        except Exception as exc:                                  # noqa: BLE001
            unreadable.append((fn, name, str(exc)))
            continue
        # A forgiven run concludes success having refreshed nothing, so where a
        # witness step exists the newest run in which it RAN is the clock. One
        # request per successful run examined, and only until the first verified
        # one: measured 2026-09-27 that is 1 request for five of the six
        # workflows with a witness and 2 for the sixth. Manager traffic and the
        # roster workflows share one account budget, which is why this is stated.
        verified_at, floor_age, checked = None, None, 0
        if witness is not None:
            for run in runs:
                if run.get("conclusion") != "success":
                    continue
                if checked >= WITNESS_RUN_LIMIT:
                    break
                checked += 1
                try:
                    jobs = api_get("/repos/%s/actions/runs/%s/jobs"
                                   % (args.repo, run.get("id")), token)
                except Exception:                                 # noqa: BLE001
                    # Unreadable is unknown, never a no: stop here and let the
                    # floor stand at whatever was actually read.
                    break
                if workflow_run_evidence.run_did_work(jobs, witness):
                    verified_at = parse_ts(run["created_at"])
                    break
                # It ran and rebuilt nothing, so the true age is at least this old.
                floor_age = (now - parse_ts(run["created_at"])).days
        verdict, detail = classify(runs, cad, now, created, state,
                                   code_changed_at(fn, own.get(fn, [])),
                                   witness, verified_at, floor_age)
        url = runs[0]["html_url"] if runs else None
        rows.append((verdict, fn, name, detail, url))

    rows.sort(key=lambda r: (VERDICT_ORDER[r[0]], r[1]))
    # NEW is reported for context but never counts as something to act on — a
    # county that shipped this week has done nothing wrong.
    # ON-DEMAND joins NEW as reported-for-context: a hand-run diagnostic that has
    # not been hand-run is not a frozen roster and must not hold the issue open.
    bad = [r for r in rows if r[0] not in ("OK", "NEW", "ON-DEMAND")]
    # UNPROVEN is shown but never fails the check: the fix is already in the
    # tree and the next scheduled run is what settles it.
    status = "fail" if any(r[0] in ("FAILING", "DISABLED") for r in rows) else (
        "warn" if bad or unreadable else "ok")

    lines = ["## Roster refresh health", ""]
    tally = lambda v: sum(1 for r in rows if r[0] == v)                # noqa: E731
    lines.append("Watched %d refresh workflow(s): %d OK, %d failing, %d disabled, "
                 "%d stale, %d never run, %d awaiting a first run after a fix, "
                 "%d too new to judge, %d run by hand, %d unmeasured.%s" % (
                     len(rows), tally("OK"), tally("FAILING"), tally("DISABLED"),
                     tally("STALE"), tally("SILENT"), tally("UNPROVEN"), tally("NEW"),
                     tally("ON-DEMAND"), tally("UNMEASURED"),
                     " %d unreadable." % len(unreadable) if unreadable else ""))
    witnessed = sum(1 for row in watched if row[4] is not None)
    if witnessed:
        lines.append("")
        lines.append("%d of them forgive a fetch that fails, so their runs conclude "
                     "success whether or not anything was refreshed. For those the "
                     "age above is the last run whose own rebuild step RAN, not the "
                     "last run that went green." % witnessed)
    lines.append("")
    if bad:
        lines += ["| state | workflow | detail | latest run |",
                  "|---|---|---|---|"]
        for verdict, fn, name, detail, url in bad:
            lines.append("| **%s** | `%s` | %s | %s |" % (
                verdict, fn, detail, "[run](%s)" % url if url else "—"))
        lines.append("")
        if any(r[0] == "UNPROVEN" for r in bad):
            lines.append("An **UNPROVEN** workflow failed, but its own code has been "
                         "edited since that run — the fix is already in the tree and "
                         "its next scheduled run is the first thing to test it. Do not "
                         "chase it; if it is still red after that run it will say "
                         "FAILING. Shared gates every workflow runs (`validate_index.py` "
                         "and the like) are deliberately not counted as \"its code\", "
                         "or one commit would mark all 53 unproven at once.")
            lines.append("")
        lines.append("A **FAILING** roster workflow opens no pull request, so the "
                     "shipped `data/app/` file keeps naming whoever it named on "
                     "its last successful run. Read the linked run: a builder "
                     "that refused the write (\"refusing to overwrite a good file\") "
                     "usually means the county's page lost a member — check the "
                     "county's own directory before lowering any floor.")
    else:
        lines.append("Every refresh workflow has succeeded within its own cadence.")
    if unreadable:
        lines += ["", "Could not read run history for: " + ", ".join(
            "`%s` (%s)" % (fn, why) for fn, _n, why in unreadable)]
    report = "\n".join(lines) + "\n"

    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            f.write(report)
    else:
        print(report)
    if args.status_file:
        with open(args.status_file, "w", encoding="utf-8") as f:
            f.write(status)
    print("check-roster-health: %s — %d watched, %d needing a look"
          % (status.upper(), len(rows), len(bad)), file=sys.stderr)


if __name__ == "__main__":
    if "--selftest" in sys.argv[1:]:
        sys.exit(selftest())
    main()
