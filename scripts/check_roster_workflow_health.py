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
    ROBOTS-REFUSED
             — it is red because its scraper read the host's robots.txt and
               declined, which is the correct outcome; reported, never chased
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

THERE IS ONE EXPECTED-FAILURE CLASS NOW, AND IT IS A REFUSAL RATHER THAN A BLOCK.
This paragraph used to say there was none and to predict what one would have to
look like — "measured first, and with the same inversion, so that RECOVERING
becomes the reportable event". That came due on 2026-09-25: ISBE publishes
`User-agent: * / Disallow: /`, il_county_clerk_scraper.py asks before its first
fetch and stops, and `update-county-clerk-roster` has been red ever since for the
one reason that is not a defect. ROBOTS_DECLINED below carries it, on those terms.

THE TWO COUNTIES THAT BLOCK EVERY AUTOMATED CLIENT ARE A DIFFERENT CASE and are
still not in any list here: Kendall and McHenry do NOT red their runs — their
scrape step carries continue-on-error and feeds a standing issue, so those
workflows are green by design and it is the WITNESS reading above, not an
expected-failure entry, that keeps this file honest about them. An outage and a
refusal do not want the same treatment, which is the distinction
validate_sources.py draws between its `blocked` flag and its `robots_declined`
one: `blocked` fetches first and inverts the report afterwards, which is right
for an outage and wrong where the request is itself the thing being asked for.

Usage:
    python3 scripts/check_roster_workflow_health.py                  # needs GH_TOKEN
    python3 scripts/check_roster_workflow_health.py --report r.md --status-file s.txt
    python3 scripts/check_roster_workflow_health.py --list           # offline: what it watches
    python3 scripts/check_roster_workflow_health.py --selftest       # offline: the verdicts

NOT GATED ON robots.txt: AUTHENTICATED READ OF THIS PROJECT'S OWN REPOSITORY.
It asks api.github.com, with this project's own token, which of districtry's
own weekly refreshes last did their work -- the API GitHub issues the token
for. No page is read and no link is followed, and the blanket rule in that
host's robots.txt is aimed at crawlers of the web interface rather than at an
account holder reading their own runs.

THE TEST IS WHOSE DATA AND WHOSE CREDENTIAL, never which host: an
unauthenticated read of a page on github.com would be gated in full. Stated
here in full rather than as a pointer at fleet_status.py, so neither reads as
an exemption extended by analogy.
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

# WHICH HOSTS REFUSE THIS PROJECT IS NOT RE-MEASURED HERE, and that is deliberate.
# validate_card_links.py already owns that question: its ROBOTS_DECLINED entries
# are measured refusals, its monthly run re-reads each host's robots.txt through
# `robots_policy` as the client this fleet crawls as, and its inversion is already
# the right way round — the refusal is expected, the LIFTING is the WARN. A second
# robots reader here would be two readers of one question, which is where this
# repository's recurring defect starts. So the table below names workflows and
# defers to that record for whether the host still refuses.
from validate_card_links import ROBOTS_DECLINED as MEASURED_REFUSALS

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOW_DIR = os.path.join(REPO_ROOT, ".github", "workflows")
API = "https://api.github.com"

# A WORKFLOW WHOSE SCRAPER DECLINES A HOST THAT REFUSES US IS NOT A BROKEN
# REFRESH, and reporting it as FAILING makes the one correct outcome look like
# the bug. `update-county-clerk-roster` is the case: ISBE publishes
# `User-agent: * / Disallow: /`, il_county_clerk_scraper.py asks before its first
# fetch and stops, the step exits non-zero, and the run is red — every part of
# that is this project obeying a refusal it measured. The roster is NOT emptied
# (Adam's ruling of 2026-09-19: a refusal stops the FETCH and never unpublishes),
# so the shipped file keeps its 101 clerks and the only thing that has stopped is
# the weekly re-read.
#
# NOTHING IS FORGIVEN TO GET THIS. The step still fails, `continue-on-error` is
# not widened, and the verdict does not read a run conclusion — it reads WHICH
# STEP failed, which is the same question #68 taught this file to ask. An entry
# names the workflow AND the step AND the host, so it cannot cover a different
# failure in the same workflow: a red pip install, a broken builder or a failing
# gate is a different step and still reads FAILING.
#
# WHY THE STEP'S OWN FAILURE IS ENOUGH TO ATTRIBUTE IT. `require_robots_allowed`
# RAISES rather than returning false, and the audit below holds that the named
# script still calls it and still names the host, while MEASURED_REFUSALS holds
# that the host still refuses. Given those, that step cannot succeed — so its
# failure is explained. What this does NOT establish is that the step has no
# SECOND problem waiting behind the refusal; the day the refusal lifts, the entry
# fails as stale and someone reads the run, which is the right time to find out.
#
# EVERY ENTRY IS RE-AUDITED EVERY RUN and FAILS when it stops describing the
# tree — the property ACCEPTED_DROPS, EXPECTED_UNREACHABLE and
# ACCEPTED_SHORTFALLS already have. The row is PRINTED either way, so a reader
# sees the refusal rather than a workflow quietly missing from the report.
ROBOTS_DECLINED = {
    "update-county-clerk-roster.yml": {
        "host": "www.elections.il.gov",
        "script": "scripts/il_county_clerk_scraper.py",
        "step": "Scrape the ISBE election-authority directory",
        "since": "2026-09-25",
        "why": "ISBE's robots.txt is 29 bytes of `User-agent: * / Disallow: /` under "
               "a Last-Modified of 12 June 2025, so it has refused this project for "
               "over a year; a byte-order mark hid it from the fleet's own reader "
               "until 2026-09-25. Run 11 (2026-09-19) was the last green one and run "
               "12 (2026-09-26) is the first to decline",
    },
}

# Workflows that are not data refreshes. Everything else in the directory is
# watched, which is what keeps a new county from being forgotten.
NOT_A_REFRESH = {
    "smoke-test.yml", "deploy-pages.yml", "validate-sources.yml",
    "engine-parity.yml", "fleet-status.yml", "release-engine.yml",
    "create-engine-tag.yml", "roster-health.yml",
    # Dispatched by hand rather than scheduled, and it refreshes no roster: it
    # reads every host's robots.txt so a batch of scrapers can be wired against
    # a measured verdict. With no cron there is no cadence to be stale against,
    # and a report that listed it would be reporting that nobody pressed the
    # button.
    "probe-robots-verdicts.yml",
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
                 "UNMEASURED": 4, "UNPROVEN": 5, "ROBOTS-REFUSED": 6, "NEW": 7,
                 "ON-DEMAND": 8, "OK": 9}

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


def audit_robots_declined(watched):
    """Re-check every ROBOTS_DECLINED entry against the tree. Returns problems.

    Offline and complete: each entry must still name a workflow this file watches,
    that workflow must still RUN the named script and still declare the named
    step, the script must still exist, still name the host and still call the
    shared robots gate, and the host must still be in the fleet's own record of
    measured refusals. Any of those failing means the entry has outlived its
    cause, which is exactly the three orphan conditions this class was ruled to
    carry — the workflow gone, the host no longer declined, or the scraper no
    longer reading that host — plus the two that make the attribution readable.

    A PROBLEM FAILS THE CHECK rather than warning, because an entry nobody has
    re-read is an entry that can excuse a real breakage. The host LIFTING its
    refusal is a WARN in validate_card_links.py, where the probe lives; here it
    arrives as this failure, the moment somebody acts on that warning and takes
    the host out of MEASURED_REFUSALS.
    """
    by_file = {row[0]: row for row in watched}
    problems = []
    for fn, dec in sorted(ROBOTS_DECLINED.items()):
        where = "ROBOTS_DECLINED[%r]" % fn
        row = by_file.get(fn)
        if row is None:
            problems.append("%s names a workflow this file does not watch — it has "
                            "left .github/workflows/ or joined NOT_A_REFRESH; retire "
                            "the entry" % where)
            continue
        path = os.path.join(WORKFLOW_DIR, fn)
        with open(path, encoding="utf-8") as f:
            wf_src = f.read()
        if not re.search(r"python3\s+" + re.escape(dec["script"]), wf_src):
            problems.append("%s says the workflow runs %s and it no longer does — "
                            "re-read the workflow before trusting the entry"
                            % (where, dec["script"]))
        names = {s["name"] for s in workflow_run_evidence.workflow_steps(wf_src)}
        if dec["step"] not in names:
            problems.append("%s names the step %r, which the workflow no longer "
                            "declares — a renamed step would make every failure in "
                            "this workflow read FAILING again, so fix the entry"
                            % (where, dec["step"]))
        script_path = os.path.join(REPO_ROOT, dec["script"])
        if not os.path.exists(script_path):
            problems.append("%s names %s, which is not in the tree"
                            % (where, dec["script"]))
        else:
            with open(script_path, encoding="utf-8") as f:
                sc_src = f.read()
            if dec["host"] not in sc_src:
                problems.append("%s says %s reads %s and that host is not named in it "
                                "any more — the scraper has been re-sourced; retire "
                                "the entry" % (where, dec["script"], dec["host"]))
            # EITHER SPELLING OF THE SEAM. `require_robots_once` wraps
            # `require_robots_allowed` with a per-host memo and raises exactly as
            # it does; reading only the inner name reported a wired scraper as
            # having stopped declining, which is the opposite of true.
            if not any(n in sc_src for n in ("require_robots_allowed",
                                             "require_robots_once")):
                problems.append("%s says %s declines, and it no longer calls the "
                                "robots seam — whatever is failing there now is "
                                "not a refusal" % (where, dec["script"]))
        if dec["host"] not in MEASURED_REFUSALS:
            problems.append("%s names %s, which validate_card_links.ROBOTS_DECLINED "
                            "no longer records as refusing us. Either the host "
                            "answers again — in which case this workflow's red run "
                            "is a real failure — or the two records have drifted"
                            % (where, dec["host"]))
    return problems


def classify(runs, cadence, now, created=None, state=None, code_at=None,
             witness=None, verified_at=None, floor_age=None,
             declined=None, failed_step=None):
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
        # A CORRECT REFUSAL IS NOT A BROKEN REFRESH. The verdict rests on WHICH
        # STEP failed, never on the run's conclusion, and only the step the entry
        # names clears it: anything else failing in this workflow still reads
        # FAILING. An unreadable jobs payload arrives here as `failed_step=None`,
        # so unknown reads as "not explained" rather than as expected.
        if declined is not None and failed_step and failed_step == declined["step"]:
            return ("ROBOTS-REFUSED",
                    "`%s` declines %s, which refuses this project, and the run "
                    "stopped at that step (`%s`) on %s. The shipped file keeps what "
                    "it last read — a refusal stops the fetch and never unpublishes. "
                    "Recorded since %s: %s"
                    % (declined["script"], declined["host"], declined["step"],
                       when.date().isoformat(), declined["since"], declined["why"]))
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
                  "UNPROVEN", "ROBOTS-REFUSED", "NEW", "ON-DEMAND", "OK"}
                 - set(VERDICT_ORDER)), [])

    # THE ROBOTS-REFUSED CLASS. The entry is the real one; what varies is which
    # step the run failed at, which is the whole of the attribution.
    dec = ROBOTS_DECLINED["update-county-clerk-roster.yml"]
    red = [run(1, "failure")] + weekly
    check("the named step failing reads ROBOTS-REFUSED",
          classify(red, 7, now, declined=dec, failed_step=dec["step"])[0],
          "ROBOTS-REFUSED")
    check("that verdict names the host and says the file keeps its last read",
          dec["host"] in classify(red, 7, now, declined=dec,
                                  failed_step=dec["step"])[1]
          and "never unpublishes" in classify(red, 7, now, declined=dec,
                                              failed_step=dec["step"])[1], True)
    # THE HALF THAT KEEPS THE ENTRY HONEST: one entry must not cover a different
    # failure in the same workflow.
    check("a DIFFERENT step failing still reads FAILING",
          classify(red, 7, now, declined=dec,
                   failed_step="Validate app + data files")[0], "FAILING")
    check("an unreadable jobs payload reads FAILING, not expected",
          classify(red, 7, now, declined=dec, failed_step=None)[0], "FAILING")
    check("a workflow with no entry is unaffected by a step name",
          classify(red, 7, now, declined=None, failed_step=dec["step"])[0],
          "FAILING")
    # A red run is what the entry explains; a green one needs no explaining.
    check("a green run carrying an entry is still OK",
          classify(weekly, 7, now, declined=dec, failed_step=None)[0], "OK")
    # An UNPROVEN downgrade must not outrank it: the code moving does not make the
    # next run any likelier to succeed while the host still refuses.
    check("ROBOTS-REFUSED outranks the UNPROVEN downgrade",
          classify(red, 7, now, code_at=now, declined=dec,
                   failed_step=dec["step"])[0], "ROBOTS-REFUSED")

    # THE AUDIT, on this tree and then broken on purpose six ways. A check that
    # has never failed has not been tested, and every one of these is a state the
    # entry could really reach.
    watched_now = discover()
    check("every ROBOTS_DECLINED entry still describes the tree",
          audit_robots_declined(watched_now), [])

    def audit_with(entry, key="update-county-clerk-roster.yml"):
        global ROBOTS_DECLINED
        keep = ROBOTS_DECLINED
        ROBOTS_DECLINED = {key: entry}
        try:
            return " | ".join(audit_robots_declined(watched_now))
        finally:
            ROBOTS_DECLINED = keep

    check("an entry naming an unwatched workflow fails",
          "does not watch" in audit_with(dec, key="no-such-workflow.yml"), True)
    # NOT build_sitemap.py: this workflow really does run that one, in its PR
    # step, so the first draft of this assertion passed for the wrong reason.
    check("an entry whose workflow no longer runs the script fails",
          "no longer does" in audit_with(
              dict(dec, script="scripts/validate_contrast.py")), True)
    check("an entry naming a step the workflow no longer declares fails",
          "no longer declares" in audit_with(dict(dec, step="Scrape it")), True)
    check("an entry naming a script that is not in the tree fails",
          "not in the tree" in audit_with(dict(dec, script="scripts/gone.py")), True)
    check("an entry whose host the scraper no longer names fails",
          "not named in it" in audit_with(dict(dec, host="example.invalid")), True)
    check("an entry whose host is no longer a measured refusal fails",
          "no longer records as refusing us" in audit_with(
              dict(dec, host="example.invalid")), True)

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
          "carrying a witness step, %d declining a host that refuses us"
          % (len(ran), len(witnessed), len(ROBOTS_DECLINED)))
    return 0

def main():
    ap = argparse.ArgumentParser()
    # THE FALLBACK IS THE REPOSITORY'S CURRENT SLUG, and it was the pre-rename one
    # until 2026-09-28. Inside Actions GITHUB_REPOSITORY is always set, so the
    # weekly job was never affected — which is exactly why it went unnoticed: the
    # default is reached only by a hand-run, where it answered HTTP 403 on all 132
    # workflows and reported "0 watched" under a WARN. A stale default is worse
    # than none, because the failure reads as the API refusing rather than as the
    # wrong address being asked.
    ap.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY",
                                                     "ThursdaysFamous/districtry"))
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
        # WHICH STEP failed, for a workflow whose scraper declines a host that
        # refuses us. One request, and only when an entry exists AND the newest
        # completed run is red — so the ordinary case costs nothing. The newest
        # COMPLETED run is the same one classify reads; taking runs[0] would ask
        # about a run still in flight.
        declined = ROBOTS_DECLINED.get(fn)
        failed_at = None
        done = [r for r in runs if r.get("status") == "completed"]
        if (declined is not None and done
                and done[0].get("conclusion") not in ("success", "cancelled",
                                                      "skipped")):
            try:
                jobs = api_get("/repos/%s/actions/runs/%s/jobs"
                               % (args.repo, done[0].get("id")), token)
            except Exception:                                     # noqa: BLE001
                # Unreadable is unknown, and unknown is not expected: with no
                # step name the verdict falls through to FAILING.
                jobs = None
            if jobs is not None:
                failed_at = workflow_run_evidence.failed_step(jobs)
        verdict, detail = classify(runs, cad, now, created, state,
                                   code_changed_at(fn, own.get(fn, [])),
                                   witness, verified_at, floor_age,
                                   declined, failed_at)
        url = runs[0]["html_url"] if runs else None
        rows.append((verdict, fn, name, detail, url))

    rows.sort(key=lambda r: (VERDICT_ORDER[r[0]], r[1]))
    # NEW is reported for context but never counts as something to act on — a
    # county that shipped this week has done nothing wrong.
    # ON-DEMAND joins NEW as reported-for-context: a hand-run diagnostic that has
    # not been hand-run is not a frozen roster and must not hold the issue open.
    # ROBOTS-REFUSED joins them, for a different reason: the workflow IS red and
    # that is the correct outcome, so it must not hold the tracking issue open.
    # It is still PRINTED below — a refusal a reader cannot see in the report is
    # a refusal the next reader re-diagnoses.
    bad = [r for r in rows if r[0] not in ("OK", "NEW", "ON-DEMAND",
                                           "ROBOTS-REFUSED")]
    expected = [r for r in rows if r[0] == "ROBOTS-REFUSED"]
    # Every ROBOTS_DECLINED entry re-read against the tree. Offline, so the
    # selftest asserts the same thing in CI, which is where it has teeth: this
    # networked path runs weekly and CI runs the selftest on every push.
    stale_entries = audit_robots_declined(watched)
    # UNPROVEN is shown but never fails the check: the fix is already in the
    # tree and the next scheduled run is what settles it.
    status = "fail" if stale_entries or any(
        r[0] in ("FAILING", "DISABLED") for r in rows) else (
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
    if expected:
        lines.append("")
        lines.append("%d of them fail because their scraper read a host's robots.txt "
                     "and declined. That is the correct outcome, not a breakage, so "
                     "it is listed below and does not hold this issue open."
                     % len(expected))
    witnessed = sum(1 for row in watched if row[4] is not None)
    if witnessed:
        lines.append("")
        lines.append("%d of them forgive a fetch that fails, so their runs conclude "
                     "success whether or not anything was refreshed. For those the "
                     "age above is the last run whose own rebuild step RAN, not the "
                     "last run that went green." % witnessed)
    lines.append("")
    shown = sorted(bad + expected, key=lambda r: (VERDICT_ORDER[r[0]], r[1]))
    if shown:
        lines += ["| state | workflow | detail | latest run |",
                  "|---|---|---|---|"]
        for verdict, fn, name, detail, url in shown:
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
        if expected:
            lines.append("A **ROBOTS-REFUSED** workflow is red because the host it "
                         "reads refuses this project in its own robots.txt, and the "
                         "scraper asks before its first fetch and stops. Nothing is "
                         "forgiven to reach that verdict: the step still fails, and "
                         "only the step the entry names clears it — anything else "
                         "failing in the same workflow still reads FAILING. The "
                         "shipped `data/app/` file keeps what it last read, because a "
                         "refusal stops the FETCH and never unpublishes. What is "
                         "reportable here is the refusal LIFTING: "
                         "`validate_card_links.py` probes those hosts monthly and "
                         "warns when one answers again, and this check then fails on "
                         "the entry until someone re-reads the run.")
            lines.append("")
        lines.append("A **FAILING** roster workflow opens no pull request, so the "
                     "shipped `data/app/` file keeps naming whoever it named on "
                     "its last successful run. Read the linked run: a builder "
                     "that refused the write (\"refusing to overwrite a good file\") "
                     "usually means the county's page lost a member — check the "
                     "county's own directory before lowering any floor.")
    else:
        lines.append("Every refresh workflow has succeeded within its own cadence.")
    if stale_entries:
        lines += ["", "### `ROBOTS_DECLINED` entries that no longer describe the tree",
                  "",
                  "Each of these excused a red workflow and has stopped being true, "
                  "so it is failing this check rather than going on excusing it."]
        for problem in stale_entries:
            lines.append("- " + problem)
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
    print("check-roster-health: %s — %d watched, %d needing a look, %d declining a "
          "host that refuses us, %d stale ROBOTS_DECLINED entry/entries"
          % (status.upper(), len(rows), len(bad), len(expected),
             len(stale_entries)), file=sys.stderr)


if __name__ == "__main__":
    if "--selftest" in sys.argv[1:]:
        sys.exit(selftest())
    main()
