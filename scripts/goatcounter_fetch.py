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


def session(tok):
    s = requests.Session()
    s.headers["User-Agent"] = "districtry-traffic/1.0 (+https://districtry.com/)"
    # The share link authenticates by query parameter and sets a cookie for the
    # rest of the session; every later request rides that cookie.
    r = s.get(SITE + "/", params={"access-token": tok}, timeout=TIMEOUT)
    if r.status_code != 200:
        sys.exit("dashboard: HTTP %d — the share token may have been rotated "
                 "or revoked." % r.status_code)
    return s, r.text


def window():
    end = datetime.date.today() - datetime.timedelta(days=1)
    start = end - datetime.timedelta(days=WINDOW_DAYS - 1)
    return start.isoformat(), end.isoformat()


def explore(s, home, start, end):
    print("dashboard: %d bytes" % len(home))
    for pat in (r'js-total-utc[^>]*>([^<]*)<', r'id="js-total-utc"[^>]*>([^<]*)<',
                r'js-total-utc.{0,120}'):
        m = re.search(pat, home, re.S)
        print("  %-34s %r" % (pat[:34], m.group(0)[:160] if m else None))
    for n, name in sorted(WIDGETS.items()):
        r = s.get(SITE + "/load-widget", timeout=TIMEOUT, params={
            "widget": n, "period-start": start, "period-end": end,
            "group": "day"})
        print("\nwidget %d (%s): HTTP %d  %d bytes  content-type=%s"
              % (n, name, r.status_code, len(r.content),
                 r.headers.get("content-type")))
        body = r.text
        try:
            j = r.json()
            print("  json keys: %s" % sorted(j))
            body = j.get("html", "")
            print("  html %d bytes" % len(body))
        except ValueError:
            print("  not json")
        print("  " + body[:1200].replace("\n", "\n  "))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--explore", action="store_true",
                    help="print each response's shape and stop")
    args = ap.parse_args()

    tok = token()
    start, end = window()
    s, home = session(tok)
    print("window %s..%s (%d days)" % (start, end, WINDOW_DAYS))
    if args.explore:
        explore(s, home, start, end)
        return
    sys.exit("only --explore is implemented so far")


if __name__ == "__main__":
    main()
