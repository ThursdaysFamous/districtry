#!/usr/bin/env python3
"""Fail when the Court of Appeals roster has gone too long without a SUCCESSFUL
verification.

WHY THIS EXISTS. `wi_coa_scraper.py` exits 75 when it could not reach
www.wicourts.gov at all, and the workflow forgives that — the cause is measured
as per-runner packet drops (issue #387), the host is reachable from CI generally,
and the remedy its own header names is drawing another runner. Forgiving it is
right and it opens a hole: a job that is green whenever it cannot ask will stay
green forever if it never asks again. Nothing else notices, because the roster
file does not change when a fetch fails and every other guard here measures
CONTENT.

So this measures the one thing none of them do — how long since the job last
actually verified the bench — and turns red when that passes a stated ceiling.
It is a NEW guard and a stricter one; it lowers no floor and excuses nothing.

WHY THE RUN HISTORY AND NOT THE DATA. Three sources were available and two are
wrong:

  * A stamp in the roster file would have to be rewritten on every successful
    run, so every run would produce a diff and a pull request even when no judge
    moved. Iowa's chair roster already carries that cost and needed a
    `substantive_changes()` helper to work around it.
  * The roster's last COMMIT date answers a different question. It moves when the
    data CHANGES, not when it is checked, so a bench correctly verified every
    week for six months and unchanged throughout would read as six months stale.
    Four appellate judges per district is exactly the roster that stays correct
    for a long time.
  * The workflow's own run history answers the question asked. It needs no data
    change, no new field and no diff.

WHY IT READS THE REBUILD STEP AND NOT THE RUN'S CONCLUSION. Asking the API for
this workflow's last SUCCESSFUL run is the obvious question and it is the wrong
one, because the run this guard executes inside concludes success as well. The
scrape step carries `continue-on-error`, the forgiven path exits 0, every step
after it is skipped by its own `if:`, and so nothing fails — a forgiven run is
recorded as a success and resets the very clock the next forgiven run reads.
Weekly forgiveness would hold the measured age at about seven days for ever and
the 60-day ceiling could never be reached at all. That was this guard's
behaviour from 2026-09-19 until 2026-09-27: the change that introduced it also
removed the condition it measures.

MEASURED RATHER THAN REASONED, on this repository's own run history.
update-mchenry-county-board-roster run 8 (2026-08-28) had a scrape step that
genuinely failed — its dependent step fired on `steps.scrape.outcome ==
'failure'` — and GitHub reported that step's `conclusion` as "success", the job
as success, and returned the run from a `?status=success` query. So a
continue-on-error step's own conclusion can never be the signal here.

What IS visible is the conditional step after it. `Rebuild the Court of Appeals
roster` runs only where the scrape exited 0, and a step skipped by its `if:`
reads "skipped" in the jobs API — unmasked, measured on that same McHenry run,
whose rebuild step reads "skipped" beside the scrape step's masked "success".
So a run verified the bench exactly when its rebuild step ran. That coupling is
gated rather than trusted: both `--selftest` and the live run read the workflow
and fail if the step is renamed or stops being conditional on the scrape's exit
code, because a silent rename would empty this guard the way the run-conclusion
reading already had.

THE SAME READING IS ELSEWHERE AND IS NOT FIXED HERE. Seven workflows in this
repository forgive a step and then skip the rest on its exit code — this one
among them — so all seven conclude success on a run that fetched nothing, and
`scripts/check_roster_workflow_health.py` classifies every roster workflow by
`conclusion == "success"` (its line 246). Measured on
update-mchenry-county-board-roster, which has that shape: four consecutive runs
— 2026-07-30, 08-20, 08-28 and 09-03 — concluded success with their rebuild step
SKIPPED, so on 2026-09-03 a run-conclusion reading answered 6.7 days old while
nothing in that workflow's successful history had reached the county at all.
Teaching that script seven different verify-step names is a design question
rather than a line, so it is recorded as a task and not attempted here.

THE CEILING IS 60 DAYS, and the number is Iowa's: `build_ia_county_chair.py`
uses 60 for how long a carried-forward name may stand.

STATING THE COST WITH ITS POPULATION. Measured 2026-09-27 over every run this
workflow has ever had — 8 runs from 2026-08-26 to 2026-09-23, five on the
schedule and three dispatched by hand — 3 of the 8 reached the court, and 1 of
the 5 scheduled ones did. A 60-day window holds about eight weekly attempts, so
the chance that none of them reaches the court is 2.3% at the all-runs rate and
16.8% at the scheduled-only rate. THE SCHEDULED FIGURE IS THE ONE THAT GOVERNS:
a 60-day window contains scheduled runs by construction and contains a dispatch
only if somebody happens to dispatch one. It is not a comfortable number and it
is not smoothed — a red is cleared by re-running to draw another runner, and the
ceiling is not raised to make it rarer.

AND THE FIGURE IS AN ORDER OF MAGNITUDE, NOT A CONFIDENCE INTERVAL. All five
failed runs died on the same exception — `URLError: <urlopen error timed out>`,
connecting to www.wicourts.gov — five for five, read from the run logs on
2026-09-27. Trials that share one cause are not independent, so raising a
per-run rate to the eighth power says roughly how big the risk is and nothing
about how sure anyone is of it. A red at 60 days is still worth a look: it is
true that nobody has verified the bench in two months.

THE EARLIER FIGURE WAS RIGHT ARITHMETIC ON AN UNSTATED POPULATION. This
paragraph read "roughly two runs in seven" and "about 6%" from 2026-09-19. Both
were correct — 2 of the 7 runs that existed that day had reached the court, and
(1 - 2/7) to the eighth is 6.8% — and a reader could not tell whether the seven
were runs, weeks or attempts, nor that on that day 0 of 4 SCHEDULED runs had
ever succeeded, which is the denominator a weekly ceiling is about.

WHEN THE API ITSELF CANNOT BE READ this exits 0 with a loud note rather than
red. Failing would make an unmeasurable condition into an error, which is the
thing this project avoids everywhere else, and the next run measures again. The
scenario that defeats it — GitHub's own API unreadable from every runner for
sixty consecutive days — is not one a ceiling can help with anyway.

Usage:
    python3 wi/scripts/wi_coa_staleness.py --ceiling-days 60
    python3 wi/scripts/wi_coa_staleness.py --selftest   # offline, no API
"""

import argparse
import datetime
import io
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "scripts"))
import workflow_run_evidence  # noqa: E402  (shared reader — do not fork)

REPO = os.environ.get("GITHUB_REPOSITORY", "ThursdaysFamous/districtry")
WORKFLOW = "update-wi-court-of-appeals-roster.yml"
DEFAULT_CEILING_DAYS = 60
UA = {"User-Agent": "districtry-wisconsin/1.0 (+https://districtry.com/wi/)"}

# The step that tells a run which reached the court from one that was forgiven.
# It is conditional on the scrape's own exit code, so it RUNS on a verification
# and reads "skipped" on a forgiven run. The scrape step itself cannot answer:
# it carries continue-on-error, whose failure GitHub masks as "success".
VERIFY_STEP = "Rebuild the Court of Appeals roster"
SCRAPE_OUTPUT = "steps.scrape.outputs.code"
WORKFLOW_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    ".github", "workflows", WORKFLOW)

# Bounded so a long forgiven streak cannot spend the run on API calls: 60
# successful runs is more than a year of this weekly job, and the walk stops at
# the first verification it finds, which is normally the newest run examined.
PER_PAGE = 30
MAX_PAGES = 2


def check_workflow_coupling(path=WORKFLOW_PATH):
    """(ok, message) — is VERIFY_STEP still the thing this guard thinks it is?

    Everything below rests on one coupling: a step that runs only where the
    scrape exited 0. Rename that step, or drop its `if:`, and this guard goes
    on reporting confidently about nothing — which is exactly the failure it
    was rewritten to end, so the coupling is checked rather than assumed. Read
    as text: the workflow is not parsed anywhere else here and this module is
    stdlib-only.
    """
    try:
        with io.open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as e:
        return False, "could not read %s (%s)" % (path, e)
    marker = "- name: %s" % VERIFY_STEP
    if marker not in text:
        return False, (
            "%s has no step named %r. This guard tells a run that reached the "
            "court from one that was forgiven by that step's conclusion, so "
            "renaming it empties the guard silently: update VERIFY_STEP in the "
            "same change." % (WORKFLOW, VERIFY_STEP))
    block = text.split(marker, 1)[1].split("\n      - name:", 1)[0]
    if SCRAPE_OUTPUT not in block:
        return False, (
            "%s's %r step no longer mentions %s in its condition. This guard "
            "reads that step as \"the scrape reached the court\"; a step that "
            "runs unconditionally would make every forgiven run look verified."
            % (WORKFLOW, VERIFY_STEP, SCRAPE_OUTPUT))
    return True, ("%r is present and still conditional on %s"
                  % (VERIFY_STEP, SCRAPE_OUTPUT))


def api_get(path, timeout=30):
    """Parsed JSON from the GitHub API. Raises; the caller decides what that means."""
    headers = dict(UA)
    headers["Accept"] = "application/vnd.github+json"
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = "Bearer %s" % token
    req = urllib.request.Request("https://api.github.com" + path, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def run_started(run):
    """The run's start as an aware datetime, or None if it carries neither key."""
    started = run.get("run_started_at") or run.get("created_at")
    if not started:
        return None
    when = datetime.datetime.strptime(started, "%Y-%m-%dT%H:%M:%SZ")
    return when.replace(tzinfo=datetime.timezone.utc)


def run_verified(jobs_payload, step=VERIFY_STEP):
    """True when this run's own `step` RAN rather than being skipped.

    ONE READER, NOT A SECOND COPY. This used to carry the classifier itself,
    five lines identical to `workflow_run_evidence.run_did_work`, which the
    fleet's roster-health watchdog and weekly fleet report both read. Two
    readers of one question is where this project's recurring defect starts,
    and here it is not hypothetical: this guard and that report would have been
    free to disagree about the same runs of the same workflow. The shared module
    is stdlib-only, so importing it costs this script nothing it did not already
    have.

    The correction itself is recorded there. In short: the obvious reading — the
    run concluded success — is true of a forgiven run too, because the scrape
    step carries continue-on-error and the steps after it are SKIPPED rather
    than failed. Measured on update-mchenry-county-board-roster run 8
    (2026-08-28), whose scrape genuinely failed: the API reported that step's
    conclusion as "success", the job as success, and a `?status=success` query
    returned the run, while its conditional rebuild step read "skipped" in the
    same payload. That is not masked, so it is the only difference the API shows.

    A run whose payload carries no such step reads as NOT verified, which is
    the safe direction; a rename that made every run read that way is what
    check_workflow_coupling() refuses.
    """
    return workflow_run_evidence.run_did_work(jobs_payload, step)


def last_verification(repo=REPO, workflow=WORKFLOW, timeout=30,
                      per_page=PER_PAGE, max_pages=MAX_PAGES):
    """(when, run_number, examined, forgiven, exhausted) for the newest run
    that actually reached the court.

    `when` is None when no verification was found inside the bound; `exhausted`
    says whether the history itself ran out (so None means "never") rather than
    the page bound being hit (so None means "not found this far back"). Walks
    successful runs newest-first and stops at the first verification, because
    a forgiven run is a success too and cannot be told apart from the run list.

    Raises on a network or API failure; the caller decides what that means.
    """
    examined = 0
    forgiven = 0
    for page in range(1, max_pages + 1):
        data = api_get(
            "/repos/%s/actions/workflows/%s/runs?status=success&per_page=%d&page=%d"
            % (repo, workflow, per_page, page), timeout=timeout)
        runs = data.get("workflow_runs") or []
        for run in runs:
            when = run_started(run)
            if when is None:
                continue
            examined += 1
            jobs = api_get("/repos/%s/actions/runs/%s/jobs"
                           % (repo, run.get("id")), timeout=timeout)
            if run_verified(jobs):
                return when, run.get("run_number"), examined, forgiven, False
            forgiven += 1
        if len(runs) < per_page:
            return None, None, examined, forgiven, True
    return None, None, examined, forgiven, False


def decide(last, now, ceiling_days):
    """(stale, age_days, message).

    `last` is the newest run that actually reached wicourts.gov, or None when
    no such run was found. Note what this is NOT: the newest run that concluded
    success, which a forgiven run also does.
    """
    if last is None:
        return True, None, (
            "no run of %s in the history read here reached wicourts.gov, so "
            "the shipped bench has not been verified by this job at all"
            % WORKFLOW)
    age = (now - last).total_seconds() / 86400.0
    if age >= ceiling_days:
        return True, age, (
            "the bench was last read from wicourts.gov %.1f days ago (%s), "
            "past the %d-day ceiling. Every run since then either failed or "
            "was forgiven for not reaching the host. Re-run this workflow to "
            "draw another runner; if it keeps failing, the roster needs a look "
            "by hand." % (age, last.date().isoformat(), ceiling_days))
    return False, age, (
        "the bench was last read from wicourts.gov %.1f days ago (%s), inside "
        "the %d-day ceiling" % (age, last.date().isoformat(), ceiling_days))


def _jobs(*steps):
    """A jobs payload in the API's own shape, from (name, conclusion) pairs."""
    return {"jobs": [{"steps": [{"name": n, "conclusion": c} for n, c in steps]}]}


def selftest():
    now = datetime.datetime(2026, 9, 19, tzinfo=datetime.timezone.utc)
    day = datetime.timedelta(days=1)
    cases = [
        ("no verification found", None, 60, True),
        ("yesterday", now - day, 60, False),
        ("59 days", now - 59 * day, 60, False),
        ("exactly 60 days", now - 60 * day, 60, True),
        ("61 days", now - 61 * day, 60, True),
        ("5 days on a 1-day ceiling", now - 5 * day, 1, True),
        ("today", now, 60, False),
    ]
    bad = 0
    for label, last, ceiling, want in cases:
        stale, age, msg = decide(last, now, ceiling)
        ok = stale == want
        bad += 0 if ok else 1
        print("  %-38s stale=%-5s expected=%-5s %s"
              % (label, stale, want, "ok" if ok else "MISMATCH"))

    # The forgiven-run cases. Each payload is the shape the API really returns;
    # the third is update-mchenry run 8's own, which is what proves a
    # continue-on-error step's masked "success" must never be read as a pass.
    verdicts = [
        ("a run whose rebuild step ran is a verification",
         _jobs(("Scrape the wicourts.gov Court of Appeals bench", "success"),
               (VERIFY_STEP, "success")), True),
        ("a run whose rebuild step was skipped is not",
         _jobs(("Scrape the wicourts.gov Court of Appeals bench", "success"),
               (VERIFY_STEP, "skipped")), False),
        ("a masked continue-on-error success is not a verification",
         _jobs(("Scrape the wicourts.gov Court of Appeals bench", "success"),
               ("Decide whether an unreachable host is forgivable", "success"),
               (VERIFY_STEP, "skipped")), False),
        ("a payload carrying no such step is not",
         _jobs(("Set up job", "success")), False),
        ("an empty payload is not",
         {"jobs": []}, False),
    ]
    for label, payload, want in verdicts:
        got = run_verified(payload)
        ok = got == want
        bad += 0 if ok else 1
        print("  %-38s verified=%-5s expected=%-5s %s"
              % (label[:38], got, want, "ok" if ok else "MISMATCH"))

    ok, msg = check_workflow_coupling()
    bad += 0 if ok else 1
    print("  %-38s %s" % ("the workflow coupling holds",
                          ("ok — " + msg) if ok else ("MISMATCH — " + msg)))

    if bad:
        sys.exit("wi-coa-staleness: --selftest FAILED on %d case(s)" % bad)
    print("wi-coa-staleness: --selftest OK — %d case(s), the boundary at the "
          "ceiling counts as stale and a forgiven run does not count as a "
          "verification" % (len(cases) + len(verdicts) + 1))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ceiling-days", type=int, default=DEFAULT_CEILING_DAYS)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    # A rename is our own tree rather than somebody's outage, so it fails here
    # rather than being forgiven with the network errors below.
    ok, why = check_workflow_coupling()
    if not ok:
        sys.exit("wi-coa-staleness: FAIL — %s" % why)

    try:
        when, number, examined, forgiven, exhausted = last_verification()
    except Exception as e:                                     # noqa: BLE001
        print("wi-coa-staleness: NOTE — could not read the run history (%s: "
              "%s), so the age of the last verification is unmeasured on this "
              "run. Passing rather than failing on something unmeasurable; the "
              "next run measures again." % (type(e).__name__, str(e)[:120]))
        return

    # Not finding one within the page bound is not the same claim as there
    # being none, so it is reported as unmeasured rather than as staleness.
    if when is None and not exhausted:
        print("wi-coa-staleness: NOTE — none of the %d most recent successful "
              "runs reached wicourts.gov, and the walk hit its %d-page bound "
              "before the history ran out, so the age is unmeasured on this "
              "run rather than proven past the ceiling."
              % (examined, MAX_PAGES))
        return

    stale, age, msg = decide(when, datetime.datetime.now(datetime.timezone.utc),
                             args.ceiling_days)
    tail = (" (%d successful run(s) examined, %d of them forgiven without "
            "reaching the host)" % (examined, forgiven))
    if stale:
        sys.exit("wi-coa-staleness: FAIL — %s%s" % (msg, tail))
    print("wi-coa-staleness: OK — %s%s" % (msg, tail))


if __name__ == "__main__":
    main()
