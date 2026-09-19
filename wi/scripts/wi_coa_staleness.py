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

THE CEILING IS 60 DAYS, and the number is Iowa's: `build_ia_county_chair.py`
uses 60 for how long a carried-forward name may stand. Stating the cost rather
than implying it — this job succeeds on roughly two runs in seven against the
same host, so across the ~8 weekly attempts inside a 60-day window the chance of
no success at all is about 6%. A red at that point is not a false alarm: it is
true that nobody has verified the bench in two months, which is worth a look.

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
import json
import os
import sys
import urllib.error
import urllib.request

REPO = os.environ.get("GITHUB_REPOSITORY", "ThursdaysFamous/districtry")
WORKFLOW = "update-wi-court-of-appeals-roster.yml"
DEFAULT_CEILING_DAYS = 60
UA = {"User-Agent": "districtry-wisconsin/1.0 (+https://districtry.com/wi/)"}


def last_success(repo=REPO, workflow=WORKFLOW, timeout=30):
    """(datetime, run_number) of the newest successful run, or None.

    Raises on a network or API failure; the caller decides what that means.
    """
    url = ("https://api.github.com/repos/%s/actions/workflows/%s/runs"
           "?status=success&per_page=1" % (repo, workflow))
    headers = dict(UA)
    headers["Accept"] = "application/vnd.github+json"
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = "Bearer %s" % token
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.load(r)
    runs = data.get("workflow_runs") or []
    if not runs:
        return None
    started = runs[0].get("run_started_at") or runs[0].get("created_at")
    when = datetime.datetime.strptime(started, "%Y-%m-%dT%H:%M:%SZ")
    return when.replace(tzinfo=datetime.timezone.utc), runs[0].get("run_number")


def decide(last, now, ceiling_days):
    """(stale, age_days, message). `last` is None when nothing ever succeeded."""
    if last is None:
        return True, None, (
            "no successful run of %s has EVER been recorded, so the shipped "
            "roster has never been verified by this job" % WORKFLOW)
    age = (now - last).total_seconds() / 86400.0
    if age >= ceiling_days:
        return True, age, (
            "last successful verification was %.1f days ago (%s), past the "
            "%d-day ceiling. The bench has not been checked against "
            "wicourts.gov in that time. Re-run this workflow to draw another "
            "runner; if it keeps failing, the roster needs a look by hand."
            % (age, last.date().isoformat(), ceiling_days))
    return False, age, (
        "last successful verification was %.1f days ago (%s), inside the "
        "%d-day ceiling" % (age, last.date().isoformat(), ceiling_days))


def selftest():
    now = datetime.datetime(2026, 9, 19, tzinfo=datetime.timezone.utc)
    day = datetime.timedelta(days=1)
    cases = [
        ("never succeeded", None, 60, True),
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
        print("  %-28s stale=%-5s expected=%-5s %s"
              % (label, stale, want, "ok" if ok else "MISMATCH"))
    if bad:
        sys.exit("wi-coa-staleness: --selftest FAILED on %d case(s)" % bad)
    print("wi-coa-staleness: --selftest OK — %d case(s), the boundary at the "
          "ceiling counts as stale" % len(cases))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ceiling-days", type=int, default=DEFAULT_CEILING_DAYS)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    try:
        last = last_success()
    except Exception as e:                                     # noqa: BLE001
        print("wi-coa-staleness: NOTE — could not read the run history (%s: "
              "%s), so the age of the last verification is unmeasured on this "
              "run. Passing rather than failing on something unmeasurable; the "
              "next run measures again." % (type(e).__name__, str(e)[:120]))
        return

    stale, age, msg = decide(last[0] if last else None,
                             datetime.datetime.now(datetime.timezone.utc),
                             args.ceiling_days)
    if stale:
        sys.exit("wi-coa-staleness: FAIL — %s" % msg)
    print("wi-coa-staleness: OK — %s" % msg)


if __name__ == "__main__":
    main()
