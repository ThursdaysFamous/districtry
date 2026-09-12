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
    SILENT   — old enough to have run, and never has
    DISABLED — switched off, so it is not refreshing anything
    NEW      — added too recently for its cron to have fired (not a problem)
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


def discover():
    """Refresh workflows on disk: (filename, display name, cadence, scripts)."""
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
                    sorted(set(RUNS_RE.findall(src)))))
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
    for _fn, _name, _cad, scripts in watched:
        for sc in scripts:
            uses[sc] = uses.get(sc, 0) + 1
    return {fn: [sc for sc in scripts if uses.get(sc) == 1]
            for fn, _name, _cad, scripts in watched}


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


def classify(runs, cadence, now, created=None, state=None, code_at=None):
    """(verdict, detail) for one workflow's recent runs, newest first."""
    if state and state != "active":
        return ("DISABLED", "workflow state is %r — it is not running at all" % state)

    young = created is not None and (now - created).days <= (cadence or 7)
    completed = [r for r in runs if r.get("status") == "completed"]
    if not completed:
        if young:
            return ("NEW", "added %d day(s) ago; its cron has not come round yet"
                    % (now - created).days)
        return ("SILENT", "no completed run on record")

    latest = completed[0]
    succeeded = [r for r in completed if r.get("conclusion") == "success"]
    last_ok = parse_ts(succeeded[0]["created_at"]) if succeeded else None
    age = (now - last_ok).days if last_ok else None

    # Cancelled and skipped runs are neither a failure nor a refresh; they only
    # matter through the staleness clock, which they do not stop.
    failing = latest.get("conclusion") not in ("success", "cancelled", "skipped")
    limit = (cadence or 7) * 2 + 2
    stale = age is None or age > limit

    if failing:
        when = parse_ts(latest["created_at"])
        detail = "latest run %s on %s; last success %s" % (
            latest.get("conclusion"), when.date().isoformat(),
            "never" if age is None else "%d days ago" % age)
        # The red predates its own fix: the code has been edited since it ran,
        # so nothing has yet tested whether the failure survives.
        if code_at is not None and code_at > when:
            return ("UNPROVEN", detail + "; but its code changed on %s, after "
                    "that run — the next scheduled run is the first to test it"
                    % code_at.date().isoformat())
        return ("FAILING", detail)
    if stale and young:
        return ("NEW", "added %d day(s) ago; not enough history to judge"
                % (now - created).days)
    if stale:
        return ("STALE", "last success %s (expected within ~%d days)"
                % ("never" if age is None else "%d days ago" % age, limit))
    return ("OK", "last success %d days ago" % age)


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
        for fn, name, cad, scripts in watched:
            print("%-46s every ~%s days   %s" % (fn, cad, name))
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
    for fn, name, cad, scripts in watched:
        wf = meta.get(fn) or {}
        created = parse_ts(wf["created_at"]) if wf.get("created_at") else None
        state = wf.get("state")
        try:
            data = api_get("/repos/%s/actions/workflows/%s/runs?per_page=20"
                           % (args.repo, fn), token)
            runs = data.get("workflow_runs") or []
        except urllib.error.HTTPError as exc:
            unreadable.append((fn, name, "HTTP %s" % exc.code))
            continue
        except Exception as exc:                                  # noqa: BLE001
            unreadable.append((fn, name, str(exc)))
            continue
        verdict, detail = classify(runs, cad, now, created, state,
                                   code_changed_at(fn, own.get(fn, [])))
        url = runs[0]["html_url"] if runs else None
        rows.append((verdict, fn, name, detail, url))

    order = {"FAILING": 0, "DISABLED": 1, "STALE": 2, "SILENT": 3,
             "UNPROVEN": 4, "NEW": 5, "OK": 6}
    rows.sort(key=lambda r: (order[r[0]], r[1]))
    # NEW is reported for context but never counts as something to act on — a
    # county that shipped this week has done nothing wrong.
    bad = [r for r in rows if r[0] not in ("OK", "NEW")]
    # UNPROVEN is shown but never fails the check: the fix is already in the
    # tree and the next scheduled run is what settles it.
    status = "fail" if any(r[0] in ("FAILING", "DISABLED") for r in rows) else (
        "warn" if bad or unreadable else "ok")

    lines = ["## Roster refresh health", ""]
    tally = lambda v: sum(1 for r in rows if r[0] == v)                # noqa: E731
    lines.append("Watched %d refresh workflow(s): %d OK, %d failing, %d disabled, "
                 "%d stale, %d never run, %d awaiting a first run after a fix, "
                 "%d too new to judge.%s" % (
                     len(rows), tally("OK"), tally("FAILING"), tally("DISABLED"),
                     tally("STALE"), tally("SILENT"), tally("UNPROVEN"), tally("NEW"),
                     " %d unreadable." % len(unreadable) if unreadable else ""))
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
    main()
