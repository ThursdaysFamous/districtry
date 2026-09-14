#!/usr/bin/env python3
"""Fetch the fleet's GoatCounter dashboard into data/goatcounter-traffic.json.

WHY THIS IS A WORKFLOW STEP. Until 2026-09-14 the traffic report was refreshed
by an agent session that held the dashboard share token in a GOAT_COUNTER
environment variable and rebuilt scratch fetch/build scripts each time. On
2026-09-14 that variable was absent from the session, the scratch scripts had
been reclaimed, and the refresh could not run at all. The token is a REPO
SECRET (measured that day: GOAT_COUNTER, BING_API_KEY and GOOGLE_SA_KEY all
report `set` inside a job), so the fetch belongs where the credential is, and
the committed JSON is the handoff to whatever draws the chart — exactly the
arrangement gsc_fetch.py already has for Search Console.

THE WINDOW IS A ROLLING TWO MONTHS, stated in DAYS because months are not all
the same length: WINDOW_DAYS ending on the last full day. It used to run from
launch (2026-07-10) and grow without bound.

--explore prints the shape of each response and no data-derived claims. It is
how the parser below was written, and it is kept because the dashboard is HTML
rather than a documented API: when a widget changes shape, the first move is to
look at it rather than to guess.

NOTHING PER-PERSON IS COLLECTED, because GoatCounter holds nothing per-person:
it is cookieless, stores no identifier, and every number here is a count.
"""

import argparse
import datetime
import json
import os
import re
import sys

import requests

SITE = "https://districtry.goatcounter.com"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "data", "goatcounter-traffic.json")

# Two months, in days. The report's first window (2026-07-10..2026-09-09) was
# 62 days, so this keeps the chart the same width it has always been.
WINDOW_DAYS = 62

# The dashboard's widget indices, learned from the dashboard itself. These are
# positional, not named, which is why --explore exists.
WIDGETS = {0: "pages", 1: "totals", 2: "referrers", 3: "campaigns",
           4: "browsers", 5: "systems", 6: "locations"}

TIMEOUT = 60


def token():
    raw = os.environ.get("GOAT_COUNTER", "").strip()
    if not raw:
        sys.exit("GOAT_COUNTER is unset — this must run where the secret is "
                 "mounted (see .github/workflows/update-traffic-data.yml).")
    return raw


def session(tok, start, end):
    """Open the share session and read the period total off the dashboard.

    TWO THINGS HERE ARE LOAD-BEARING, both measured on 2026-09-14.

    The share link authenticates by query parameter and sets a cookie for the
    rest of the session; every later request rides that cookie.

    And the dashboard must be asked for THE SAME PERIOD the widgets will be,
    because js-total-utc is that period's total and every widget takes it as a
    parameter. Asked with no period it answers the default one — 561 against a
    two-month window — and a widget handed that number reports the wrong
    share of the wrong whole.
    """
    s = requests.Session()
    s.headers["User-Agent"] = "districtry-traffic/1.0 (+https://districtry.com/)"
    r = s.get(SITE + "/", timeout=TIMEOUT, params={
        "access-token": tok, "period-start": start, "period-end": end})
    if r.status_code != 200:
        sys.exit("dashboard: HTTP %d — the share token may have been rotated "
                 "or revoked." % r.status_code)
    m = re.search(r'js-total-utc"?>([\d,]+)<', r.text)
    if not m:
        sys.exit("dashboard: no js-total-utc in %d bytes. The dashboard's "
                 "markup has changed; run --explore." % len(r.text))
    return s, int(m.group(1).replace(",", ""))


def widget(s, n, total, start, end, **extra):
    """One load-widget call. Returns its html.

    total is not optional: without it widget 0 answers HTTP 400 and the
    horizontal-bar widgets answer "Nothing to display" — measured 2026-09-14,
    which is what the first version of this script got back.
    """
    params = dict({"widget": n, "period-start": start, "period-end": end,
                   "group": "day", "total": total}, **extra)
    r = s.get(SITE + "/load-widget", params=params, timeout=TIMEOUT)
    if r.status_code != 200:
        sys.exit("widget %s: HTTP %d" % (n, r.status_code))
    try:
        return r.json().get("html", "")
    except ValueError:
        sys.exit("widget %s: not JSON (%d bytes)" % (n, len(r.content)))


def window():
    end = datetime.date.today() - datetime.timedelta(days=1)
    start = end - datetime.timedelta(days=WINDOW_DAYS - 1)
    return start.isoformat(), end.isoformat()


def explore(s, total, start, end):
    """Print the shape of each response. Prints no URL — the token is in it."""
    print("period total (js-total-utc): %d" % total)
    calls = [(1, "totals", {}), (1, "totals is:pageview", {"filter": "is:pageview"}),
             (0, "pages", {}), (0, "pages is:event", {"filter": "is:event"}),
             (0, "pages layer/", {"filter": "layer/"}),
             (0, "pages is:pageview", {"filter": "is:pageview"}),
             (2, "referrers", {}), (3, "campaigns", {}), (4, "browsers", {}),
             (5, "systems", {}), (6, "locations", {})]
    for n, name, extra in calls:
        html = widget(s, n, total, start, end, **extra)
        body = re.sub(r"[ \t]*\n[ \t\n]*", "\n", html).strip()
        # Drop the header block; what matters is the rows under it.
        cut = body.find("</div>")
        rows = body[cut + 6:] if cut > 0 else body
        print("\n--- widget %d (%s): %d bytes ---" % (n, name, len(html)))
        print(rows[:900])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--explore", action="store_true",
                    help="print each response's shape and stop")
    args = ap.parse_args()

    tok = token()
    start, end = window()
    s, total = session(tok, start, end)
    print("window %s..%s (%d days)" % (start, end, WINDOW_DAYS))
    if args.explore:
        explore(s, total, start, end)
        return
    sys.exit("only --explore is implemented so far")


if __name__ == "__main__":
    main()
