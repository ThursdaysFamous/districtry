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
import html as html_lib
import json
import os
import re
import sys

import requests

SITE = "https://districtry.goatcounter.com"
# ROBOTS.TXT IS NOT READ HERE, DELIBERATELY, AND THIS IS THE ONE PLACE IN THE
# FLEET THAT ARGUMENT IS MADE. The host serves `User-agent: * / Disallow: /`
# (26 bytes, measured 2026-09-30), which under this project's own rule would
# stop the traffic report. It does not apply: robots.txt is a protocol for
# CRAWLERS reading a site's public pages, and this is an AUTHENTICATED request
# to districtry's OWN account with districtry's own share token, reading
# districtry's own visit counts. GoatCounter's blanket rule keeps search
# engines out of customer dashboards; it is not a site telling its own account
# holder not to read their own statistics, and the token is the service's
# documented way of doing exactly that.
#
# THE TEST IS WHOSE DATA AND WHOSE CREDENTIAL, not which host. Nothing else in
# this repository reaches a host on those terms -- every other fetch is an
# unauthenticated read of somebody else's public pages, where the rule binds in
# full and is obeyed without exception. If a second authenticated
# own-account fetch ever appears, it belongs under this reasoning and not under
# a widening of the crawl rule.
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "data", "goatcounter-traffic.json")

# Two months, in days. The report's first window (2026-07-10..2026-09-09) was
# 62 days, so this keeps the chart the same width it has always been.
WINDOW_DAYS = 62

# The shorter windows the report's timeframe buttons offer, each read whole
# off the dashboard for its own period rather than cut out of the two-month
# one: the bar lists (apps, layers, browsers, countries) are period totals
# with no day in them, so a seven-day list cannot be derived from a sixty-two
# day one. Adam chose "every section follows the button" on 2026-10-22, at
# the cost of asking the dashboard for each list once per window.
PRESET_DAYS = (7, 14, 30)

# The dashboard's widget indices, learned from the dashboard itself. These are
# positional, not named, which is why --explore exists.
# The dashboard's widget indices, read off the dashboard's own containers and
# each widget's own heading on 2026-09-14: 0 pages, 1 totals, 2 referrers,
# 3 campaigns, 4 browsers, 5 systems, 6 locations, 7 languages, 8 sizes.
# There is no widget 9; asking for one is an HTTP 500.

# The day the Illinois app moved from "/" to "/il/" and the fleet landing page
# took the root path.
ROOT_MOVED = "2026-08-24"

# A dashboard answering nothing is a revoked token, not a quiet two months.
MIN_PAGEVIEWS = 1

TIMEOUT = 60

# The dashboard HTML of the last session(), kept for --explore to look at,
# and whether the last widget said its list was cut short.
DASH = []
MORE = []


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
    # TWO REQUESTS, NOT ONE. The share link redirects once to set its cookie,
    # and a redirect drops the query string with it — asked for a period in the
    # same request as the token, the dashboard answered its DEFAULT period's
    # total (561 against a two-month window, measured 2026-09-14). Authenticate
    # first, then ask the authenticated session for the period.
    r = s.get(SITE + "/", timeout=TIMEOUT, params={"access-token": tok})
    if r.status_code != 200:
        sys.exit("dashboard: HTTP %d — the share token may have been rotated "
                 "or revoked." % r.status_code)
    r = s.get(SITE + "/", timeout=TIMEOUT,
              params={"period-start": start, "period-end": end})
    if r.status_code != 200:
        sys.exit("dashboard for %s..%s: HTTP %d" % (start, end, r.status_code))
    DASH.append(r.text)
    return s, read_total(r.text)


def read_total(text):
    m = re.search(r'js-total-utc"?>([\d,]+)<', text)
    if not m:
        sys.exit("dashboard: no js-total-utc in %d bytes. The dashboard's "
                 "markup has changed; run --explore." % len(text))
    return int(m.group(1).replace(",", ""))


def period_total(s, start, end):
    """The dashboard's own total for a period, on an authenticated session."""
    r = s.get(SITE + "/", timeout=TIMEOUT,
              params={"period-start": start, "period-end": end})
    if r.status_code != 200:
        sys.exit("dashboard for %s..%s: HTTP %d" % (start, end, r.status_code))
    return read_total(r.text)


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
        # GoatCounter's error page is mostly stylesheet; the message is the
        # only part worth printing, and the URL is never printed because the
        # token is in the session rather than in it.
        # GoatCounter's error page is mostly stylesheet; the message sits
        # after the last </style>, which is why the first version of this
        # printed CSS and said nothing.
        body = r.text.rsplit("</style>", 1)[-1]
        note = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body)).strip()
        sys.exit("widget %s: HTTP %d — %s" % (n, r.status_code, note[:400]))
    try:
        body = r.json()
    except ValueError:
        sys.exit("widget %s: not JSON (%d bytes)" % (n, len(r.content)))
    # "more" is the widget saying its list is cut short. It is carried out of
    # here rather than dropped, because a truncated list that looks complete
    # is how a total silently stops adding up.
    MORE.clear()
    MORE.append(bool(body.get("more")))
    return body.get("html", "")


def window():
    end = datetime.date.today() - datetime.timedelta(days=1)
    start = end - datetime.timedelta(days=WINDOW_DAYS - 1)
    return start.isoformat(), end.isoformat()


def series(html):
    """The daily counts out of a totals widget.

    The series is not in the markup as rows — it is the chart's own
    data-stats attribute, an HTML-escaped JSON list of
    {day, hourly[], daily, ...}. Reading the attribute is exact where
    scraping a chart's <rect>s would be an estimate.
    """
    m = re.search(r'data-stats="([^"]*)"', html)
    if not m:
        raise SystemExit("totals widget carries no data-stats; the dashboard's "
                         "markup has changed — run --explore.")
    stats = json.loads(html_lib.unescape(m.group(1)))
    return {row["day"]: row.get("daily", 0) for row in stats}


def rows(html):
    """The (key, label, count) rows out of a horizontal-bar widget.

    data-key is the value; the .cutoff span is what a reader sees, and the two
    differ where GoatCounter resolves a code to a name (US -> United States).
    The count is the LAST col-count span, because the first carries the
    percentage, and its thousands separator is a narrow no-break space rather
    than a comma.
    """
    out = []
    for block in re.split(r'(?=<div class="[^"]*" data-key=)', html)[1:]:
        key = re.search(r'data-key="([^"]*)"', block)
        label = re.search(r'<span class="cutoff">([^<]*)</span>', block)
        counts = re.findall(r'<span class="col-count">([^<]*)</span>', block)
        if not key or not counts:
            continue
        digits = re.sub(r"[^\d]", "", counts[-1])
        if not digits:
            continue
        out.append({"key": html_lib.unescape(key.group(1)),
                    "label": html_lib.unescape(label.group(1)) if label else None,
                    "count": int(digits)})
    return out


def pages(html):
    """The (path, title, count) rows out of the pages widget.

    Different markup from the bar widgets: a table whose every row carries the
    path as its id and the count as data-count, so nothing has to be read out
    of a rendered number. The per-row chart's data-stats carries that path's
    own daily series, which is what splits the root path at the rename.
    """
    out = []
    for block in re.split(r'(?=<tr id=")', html)[1:]:
        path = re.search(r'<tr id="([^"]*)"', block)
        count = re.search(r'data-count="(\d+)"', block)
        if not path or not count:
            continue
        title = re.search(r'<small class="page-title ?[^"]*">([^<]*)</small>',
                          block)
        pid = re.search(r'<tr id="[^"]*"[^>]*\bdata-id="(\d+)"', block)
        row = {"path": html_lib.unescape(path.group(1)).strip(),
               "id": int(pid.group(1)) if pid else None,
               "title": html_lib.unescape(title.group(1)).strip() if title else None,
               "count": int(count.group(1))}
        try:
            row["daily"] = series(block)
        except SystemExit:
            row["daily"] = {}
        out.append(row)
    return out


LAYER_PREFIX = "layer/"
MAP_LINK_PREFIX = "map-link-read/"


def map_links(s, total, start, end, mx, tags):
    """Every `map-link-read/` row, past the dashboard's ten-row cap.

    One filtered request first; only when that list is cut short is each app
    (and the front page, `front`) asked for on its own, the way
    layer_instances() gets past the same cap. Returns (rows, cut): cut is true
    when even a per-app list was cut short, so the report can say its counts
    are a floor rather than present a short list as complete.
    """
    rows_ = pages(widget(s, 0, total, start, end, max=mx, filter=MAP_LINK_PREFIX))
    if not (MORE and MORE[0]):
        return sorted(rows_, key=lambda r: (-r["count"], r["path"])), False
    got, cut = {}, False
    for tag in list(tags) + ["front"]:
        for r in pages(widget(s, 0, total, start, end, max=mx,
                              filter=MAP_LINK_PREFIX + tag + "/")):
            if r["path"].startswith(MAP_LINK_PREFIX + tag + "/"):
                got[r["path"]] = r
        cut = cut or bool(MORE and MORE[0])
    return sorted(got.values(), key=lambda r: (-r["count"], r["path"])), cut


def layer_instances(s, total, start, end, mx, tags, fleet_rows):
    """Each instance's own layer ranking, one filtered request per tag.

    The layer event has carried the instance tag since 2026-09-29 (engine
    overlay-cards): `layer/<tag>/<id>`. Before that it was `layer/<id>` for
    every app, so two instances registering the same layer id reported into one
    row and nothing could say which state a toggle came from.

    ONE REQUEST PER INSTANCE is what gets past the dashboard's TEN-ROW CAP, and
    that is the whole reason this is worth doing. 102 distinct layer ids across
    the fleet already compete for those ten slots — which is why the fleet-wide
    `layer/` list comes back as exactly ten rows rather than a full one — and
    splitting each shared id per instance makes it 157 (id, instance) pairs
    competing for the same ten. Asked per instance, Illinois's 40 rank inside
    their own ten. Without this the split would be a straight regression.

    THE BROKEN-FILTER CASE IS CHECKED RATHER THAN HOPED FOR. On the first runs
    after the engine change a per-instance request legitimately returns
    NOTHING, because no toggle has been recorded under the new path yet — which
    is indistinguishable from a nested `filter=` that does not work, and the
    filter is a dashboard query string rather than a documented API. So the
    fleet-wide rows are the control: if THEY carry a new-shape path for a tag
    whose own request came back empty, the filter is broken and this fails
    rather than publishing an instance as having no toggles.

    Returns {(tag, id): count}.
    """
    out = {}
    empty = []
    for tag in tags:
        rows = pages(widget(s, 0, total, start, end, max=mx,
                            filter=LAYER_PREFIX + tag + "/"))
        found = 0
        for r in rows:
            parts = r["path"].split("/")
            if len(parts) == 3 and parts[0] == "layer" and parts[1] == tag:
                out[(tag, parts[2])] = r["count"]
                found += 1
        if not found:
            empty.append(tag)
    # The control. A fleet-wide row of the new shape proves the tag is being
    # recorded, so an empty per-instance request for it cannot be day-one.
    seen_in_fleet = {r["path"].split("/")[1] for r in fleet_rows
                     if len(r["path"].split("/")) == 3}
    broken = sorted(set(empty) & seen_in_fleet)
    if broken:
        sys.exit("the per-instance layer filter returned nothing for %s while "
                 "the fleet-wide list carries layer/<tag>/<id> rows for it, so "
                 "filter=%r is not doing what this assumed. Look at the widget "
                 "with --explore before trusting these rows."
                 % (", ".join(broken), LAYER_PREFIX + broken[0] + "/"))
    return out


def sum_layer_shapes(fleet_rows, per_instance):
    """One row per layer id, summing the OLD pooled shape and the new ones.

    BOTH SHAPES ARE SUMMED, so a bar keeps its whole count across the seam.
    The window is a rolling 62 days, so for 62 days after the engine change the
    old `layer/<id>` rows decay out while `layer/<tag>/<id>` fills in, and
    neither is the whole count on its own. Summing keeps the total honest and
    leaves the ATTRIBUTION partial, which the page states with its own date
    rather than implying the split is complete.
    """
    totals = {}
    for r in fleet_rows:
        parts = r["path"].split("/")
        if len(parts) == 2 and parts[0] == "layer":
            totals[parts[1]] = totals.get(parts[1], 0) + r["count"]
        elif len(parts) == 3 and parts[0] == "layer":
            totals[parts[2]] = totals.get(parts[2], 0) + r["count"]
    for (tag, lid), n in per_instance.items():
        # A fleet-wide row already counted is not counted twice: the fleet list
        # and the per-instance list overlap wherever a new-shape row is in both
        # top tens.
        key = "layer/%s/%s" % (tag, lid)
        if any(r["path"] == key for r in fleet_rows):
            continue
        totals[lid] = totals.get(lid, 0) + n
    return [{"path": "layer/" + lid, "title": "layer/" + lid, "count": n}
            for lid, n in totals.items()]


VISIT_PREFIX = "visit/"
VISITS_SINCE = "2026-10-22"


def return_visits(s, total, start, end, mx, events):
    """How many app visits were a first visit and how many a return, per day.

    Every app counts `visit/first/<tag>` or `visit/return/<tag>` once per
    browser window, decided by a mark in local storage (engine block
    `install-app`, since 2026-10-22). Seventeen apps make up to 34 paths, past
    the pages list's ten-row cap, so the per-day counts are read from the
    totals widget with a path filter instead, one request for each kind.

    THE FILTER ON THE TOTALS WIDGET IS AN ASSUMPTION, not a documented API, so
    it is checked against the pages list for the same filter: the totals must
    be at least the list's own rows (which can only be fewer, being capped)
    and no more than every event in the period. A pair that fails either test
    is printed and recorded as None, so the rest of the refresh still writes
    and the page shows no figure rather than a wrong one.
    """
    out = {"since": VISITS_SINCE}
    for kind in ("first", "return"):
        prefix = VISIT_PREFIX + kind + "/"
        days = series(widget(s, 1, total, start, end, filter=prefix))
        listed = pages(widget(s, 0, total, start, end, max=mx, filter=prefix))
        if any(not r["path"].startswith(prefix) for r in listed):
            print("WARN visit filter %r matched other paths: %s"
                  % (prefix, sorted({r["path"] for r in listed})[:5]))
            return None
        n, shown = sum(days.values()), sum(r["count"] for r in listed)
        print("visits %s: %d by day, %d in the %d listed rows"
              % (kind, n, shown, len(listed)))
        if n < shown or n > events:
            print("WARN visit counts do not reconcile for %r: %d by day, %d "
                  "listed, %d events in the period" % (prefix, n, shown, events))
            return None
        out[kind] = n
        out[kind + "_daily"] = [days.get(d, 0) for d in sorted(days)]
        out["by_app_" + kind] = sorted(
            ({"tag": r["path"][len(prefix):], "count": r["count"]}
             for r in listed), key=lambda r: (-r["count"], r["tag"]))
    return out


def top(rows, n=10):
    return [{k: v for k, v in r.items() if k != "daily"}
            for r in sorted(rows, key=lambda r: -r["count"])[:n]]


def fleet_tags():
    with open(os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "metros.json"), encoding="utf-8") as f:
        return [m["tag"] for m in json.load(f)["metros"] if m.get("tag")]


def explore(s, total, start, end):
    """Print the shape of each response. Prints no URL — the token is in it."""
    print("period total (js-total-utc): %d" % total)
    print("\n--- dashboard widget containers ---")
    for m in re.findall(r"<div[^>]*data-widget[^>]*>", DASH[0])[:14]:
        print("  " + m[:200])
    html = widget(s, 1, total, start, end)
    mx = re.search(r'data-max="(\d+)"', html).group(1)
    print("data-max: %s" % mx)
    for n in range(10):
        try:
            h = widget(s, n, total, start, end, max=mx)
        except SystemExit as e:
            print("widget %d: %s" % (n, str(e)[:160]))
            continue
        head = re.search(r"<h2>([^<]*)", h)
        print("widget %d: %-16s %d bytes" % (n, (head.group(1).strip()
                                                 if head else "?"), len(h)))


def collect(s, total, start, end, per_day=True):
    """Everything the traffic report reads, in one pass over the dashboard.

    per_day=False leaves out the per-day referrer lists, which are about the
    last REF_DAYS days whatever the window and are read once, for the full one.
    """
    hits = widget(s, 1, total, start, end)
    mx = re.search(r'data-max="(\d+)"', hits)
    if not mx:
        sys.exit("totals widget carries no data-max; run --explore.")
    mx = mx.group(1)
    hits, views = series(hits), series(
        widget(s, 1, total, start, end, filter="is:pageview"))

    daily = []
    for date in sorted(hits):
        pv = views.get(date, 0)
        # Events are what is left of the hits once the pageviews are taken
        # out: GoatCounter counts a layer toggle and a page load in the same
        # series, and the report draws them as two bands.
        daily.append({"date": date, "pageviews": pv,
                      "events": hits[date] - pv})

    page_rows, pages_truncated = all_pages(s, total, start, end, mx)
    event_rows = pages(widget(s, 0, total, start, end, max=mx,
                              filter="is:event"))
    # THE EVENTS LIST IS CAPPED AT TEN ROWS AND THE PAGE NEEDS A ROW THAT FELL
    # OFF IT. `geolocate-success` sat LOWEST of the ten for five days running
    # — 55, 53, 51, 51, 52 — and on 2026-09-23 `layer/county` at 53 pushed it
    # out. Nothing about geolocation changed; it stopped being measured, and
    # the page went on to publish "Geolocation succeeds 0% of the time it is
    # tried: 0 of 88", which is a false statement about the product.
    #
    # So the two geolocate rows are asked for BY NAME rather than hoped for in
    # a ranking, the way `layer/` already is. One extra request covers both,
    # and `geolocate` itself was the next to go: at 88 it sits one row above
    # the cut. `select` (502) and `address-search` (284) are far from it and
    # are left to the ranked list.
    event_rows += [r for r in pages(widget(s, 0, total, start, end, max=mx,
                                           filter="geolocate"))
                   if r["path"] not in {e["path"] for e in event_rows}]
    # Why "Use my current location" did not end in a point, by app and reason
    # (`locate-fail/<tag>/<reason>`, sent since 2026-10-11). Asked for by name
    # for the same reason as the geolocate rows above, and kept apart from
    # them. This list is capped at ten rows too, so it is the ten most common
    # app-and-reason pairs, not every one.
    locate_fail_rows = pages(widget(s, 0, total, start, end, max=mx,
                                    filter="locate-fail/"))
    map_link_rows, map_links_cut = map_links(s, total, start, end, mx,
                                             fleet_tags())
    fleet_layer_rows = pages(widget(s, 0, total, start, end, max=mx,
                                    filter=LAYER_PREFIX))
    per_instance = layer_instances(s, total, start, end, mx, fleet_tags(),
                                   fleet_layer_rows)
    layer_rows = sum_layer_shapes(fleet_layer_rows, per_instance)

    visits = return_visits(s, total, start, end, mx, sum(d["events"] for d in daily))

    out = {
        "total": total,
        "daily": daily,
        "pageviews": sum(d["pageviews"] for d in daily),
        "events": sum(d["events"] for d in daily),
        "pages": top(page_rows, 20),
        "top_events": top(event_rows, 20),
        "locate_fail": top(locate_fail_rows, 10),
        # Every Google Maps / Apple Maps link the search boxes read
        # (`map-link-read/<tag>/<source>/<form>/<via>/<outcome>`, sent since
        # 2026-10-17), one row per combination, and whether any list it was
        # read from was cut short.
        "map_links": [{"path": r["path"], "count": r["count"]}
                      for r in map_link_rows],
        "map_links_cut": map_links_cut,
        "layers": top(layer_rows, 20),
        # The ATTRIBUTED part: one row per (instance, layer) the new event
        # shape has recorded. Empty on the first runs after the engine change
        # and fills in over the window; the page subtracts it from each id's
        # total to say how much is still pooled.
        "layer_instances": sorted(
            ({"tag": tag, "id": lid, "count": n}
             for (tag, lid), n in per_instance.items()),
            key=lambda r: (-r["count"], r["tag"], r["id"])),
        "instances": split_by_instance(page_rows),
        "pages_truncated": bool(pages_truncated),
        # First and return visits to the apps, per day (`visit/first/<tag>`
        # and `visit/return/<tag>`, sent since 2026-10-22). None when the
        # dashboard's answer did not reconcile; see return_visits().
        "visits": visits,
    }
    # THE INSTANCE BARS MUST SUM TO THE PAGEVIEW TOTAL, and they are counted
    # two different ways: the total off the totals widget, the split off the
    # pages list. The pages list caps at ten rows, so every pageview below
    # rank ten is in the first and not the second. That difference is a row of
    # its own rather than a rounding nobody sees.
    #
    # THE OLD CEILING WAS 5% AND IT WAS MEASURED THE DAY BEFORE THE CHANGE
    # THAT INVALIDATED IT. This guard was written on 2026-09-14 against a
    # residual of 9 of 1,232 (0.73%), when 52 of the site's 245 pages carried
    # the counter and almost all traffic landed on the ten instance roots. The
    # 2026-09-15 rollout put the tag on 191 more pages, so the tail below rank
    # ten became the per-county and question pages and started growing. Daily,
    # off this file's own history:
    #
    #     09-14   9 / 1,232  0.73%      09-18  41 / 1,356  3.02%
    #     09-15   9 / 1,258  0.72%      09-19  51 / 1,362  3.74%
    #     09-16  12 / 1,291  0.93%      09-20  61 / 1,388  4.39%
    #     09-17  28 / 1,325  2.11%      09-21  71 / 1,410  5.04%  <- refused
    #
    # The residual grew about 10 a day and a 5%-of-pageviews ceiling grew about
    # 1.3, so they were always going to cross; on 2026-09-21 they did, by ONE,
    # and the report could not refresh. The tail is unbounded by construction
    # now — ten rows against 243 counted pages — so no small fraction of it can
    # mean "error".
    #
    # WHAT IS STILL AN ERROR: a negative residual, which says the split
    # double-counted and is impossible; and a pages list that collapsed, which
    # drives attributed toward zero and the residual toward 100%. The ceiling
    # is set where the ten rows stop describing most of the site rather than
    # where the tail stops being tidy, and a reader is told the number either
    # way — the page draws the residual as its own row and says it cannot tell
    # what is in it.
    #
    # AND IT IS PRINTED EVERY RUN, which is the actual fix: this number grew
    # for six days with nothing reporting it until it tripped a threshold.
    attributed = sum(r["count"] for r in out["instances"])
    residual = out["pageviews"] - attributed
    share = residual / out["pageviews"] * 100 if out["pageviews"] else 0
    print("instance split: %d of %d pageviews attributed to the listed "
          "rows, %d on the long tail (%.2f%%)"
          % (attributed, out["pageviews"], residual, share))
    if residual < 0 or share > 40:
        sys.exit("the instance split does not reconcile: %d pageviews in the "
                 "totals widget, %d attributed from the pages list, %d (%.2f%%) "
                 "unaccounted. The ten-row cap explains a positive difference; "
                 "a negative one or a majority on the tail does not."
                 % (out["pageviews"], attributed, residual, share))
    if residual:
        out["instances"].append({"key": "(not in the pages list)",
                                 "count": residual})
    for n, name in [(2, "referrers"), (3, "campaigns"), (4, "browsers"),
                    (5, "systems"), (6, "locations"), (7, "languages"),
                    (8, "sizes")]:
        out[name] = rows(widget(s, n, total, start, end))
    # Last, because it changes the session's period: everything above is read
    # against the window, and this asks the dashboard about one day at a time.
    if per_day:
        out["daily_referrers"] = daily_referrers(s, end)
    return out


def preset_windows(s, end):
    """Each PRESET_DAYS window ending on `end`, read for its own period.

    The dashboard is asked for the period first, because js-total-utc is that
    period's total and every widget takes it as a parameter (see session()).
    The daily series is dropped: it is the full window's, cut to length.
    """
    out = {}
    last = datetime.date.fromisoformat(end)
    for n in PRESET_DAYS:
        start = (last - datetime.timedelta(days=n - 1)).isoformat()
        total = period_total(s, start, end)
        print("window %s..%s (%d days)" % (start, end, n))
        w = collect(s, total, start, end, per_day=False)
        del w["daily"]
        out[str(n)] = dict({"start": start, "end": end, "days": n}, **w)
    return out


# How many of the window's last days get a referrer list of their own.
REF_DAYS = 14
# Pages of a referrer list asked for before giving up on reaching its end.
REF_PAGES = 6


def all_rows(s, n, total, start, end):
    """Every row of a bar widget, following its "show more" by offset.

    THE OFFSET IS AN ASSUMPTION ABOUT A DASHBOARD THAT PUBLISHES NO API, so it
    is checked rather than trusted: a page that repeats a key already read, or
    adds nothing, means the offset did nothing, and the list is returned with
    `more` still true. A list cut short must say so, because a breakdown that
    looks complete while missing its smaller rows is how a total silently
    stops adding up.
    """
    out, seen = [], set()
    for _ in range(REF_PAGES):
        page = rows(widget(s, n, total, start, end, offset=len(out)))
        more = bool(MORE and MORE[0])
        fresh = [r for r in page if r["key"] not in seen]
        if len(fresh) < len(page) or not fresh:
            return out, True if out else more
        out += fresh
        seen.update(r["key"] for r in fresh)
        if not more:
            return out, False
    return out, True


# Pages of the pages list asked for before giving up on reaching its end. Ten
# rows a page; 254 pages carried the counter on 2026-10-20, so 60 leaves room.
PAGE_PAGES = 60


def all_pages(s, total, start, end, mx):
    """Every row of the pages list, following its "show more" by offset.

    THE TEN-ROW CAP IS WHY AN APP READ 0. The per-app bars are summed from
    this list, and until 2026-10-20 only its first ten rows were read, so an
    app whose busiest page sat below rank ten had a bar of 0 while its visits
    sat in the long-tail row. Measured on 2026-10-20's file, eight of fifteen
    apps (SF, MN, KY, NC, OK, TN, AR, MS) read 0 and 1,103 pageviews were on
    the tail.

    The pages widget takes `exclude`, a comma list of path ids
    (handlers/dashboard.go in GoatCounter's source, read 2026-10-20), but that
    is a dashboard parameter rather than a documented API, so it is checked
    rather than trusted, the way all_rows() checks offset: a page repeating a
    path already read, or adding nothing, means the exclude did nothing, and
    the list is returned with its `more` still true so the residual row stays
    honest. Returns (rows, cut).
    """
    out, seen = [], set()
    for _ in range(PAGE_PAGES):
        # GoatCounter's own "show more" on this list sends the numeric ids of
        # the rows already shown as `exclude`; a plain `offset` was tried
        # first and on 2026-10-20 returned the same ten rows. The opening tag
        # of the first row is printed once, because it is the only way to see
        # the markup this depends on without the token.
        ids = [r["id"] for r in out if r.get("id") is not None]
        extra = {"exclude": ",".join(map(str, ids))} if ids else {}
        html = widget(s, 0, total, start, end, max=mx, filter="is:pageview",
                      **extra)
        if not out:
            first = re.search(r'<tr id="[^>]*>', html)
            print("pages list: first row tag %s"
                  % (first.group(0)[:200] if first else "(none)"))
        page = pages(html)
        more = bool(MORE and MORE[0])
        fresh = [r for r in page if r["path"] not in seen]
        if out and len(ids) < len(out):
            print("pages list: rows carry no id to exclude, stopped at %d"
                  % len(out))
            return out, more
        if len(fresh) < len(page) or not fresh:
            print("pages list: exclude stopped after %d rows" % len(out))
            return out, True if out else more
        out += fresh
        seen.update(r["path"] for r in fresh)
        if not more:
            print("pages list: all %d rows read" % len(out))
            return out, False
    print("pages list: stopped at %d rows, list still cut short" % len(out))
    return out, True


def daily_referrers(s, end):
    """Where each of the last REF_DAYS days' visits came from, one day at a time.

    WHY ONE REQUEST PER DAY. The referrer widget answers for the period it is
    asked about and has no daily series, so the two-month list says nothing
    about which day a source sent its visits. The first look at the question
    (2026-10-16) worked it out by subtracting one day's saved two-month list
    from the next, which breaks whenever a source enters or leaves the top six
    and read 9 October as Yahoo +77 and Bluesky -76. Asking each day for
    itself is exact.

    Each day is asked with ITS OWN total, for the reason session() gives: a
    widget handed another period's total reports the wrong share of the wrong
    whole.
    """
    last = datetime.date.fromisoformat(end)
    out = []
    for back in range(REF_DAYS - 1, -1, -1):
        day = (last - datetime.timedelta(days=back)).isoformat()
        total = period_total(s, day, day)
        if total:
            got, more = all_rows(s, 2, total, day, day)
        else:
            got, more = [], False
        out.append({"date": day, "total": total, "rows": got, "more": more})
        print("referrers %s: %d rows, sum %d of total %d%s"
              % (day, len(got), sum(r["count"] for r in got), total,
                 ", list cut short" if more else ""))
    return out


def split_by_instance(page_rows):
    """Pageviews per instance, by path.

    THE ROOT PATH BELONGS TO TWO DIFFERENT THINGS AND THE DATE SAYS WHICH. The
    Illinois app served at "/" until it moved to "/il/" on 2026-08-24, and the
    fleet landing page has served at "/" since. The old rule for this was
    prose in the refresh instructions; here it is arithmetic, because every
    row carries its own daily series — a root pageview before the move is
    Illinois's and one on or after it is the landing page's, one day at a
    time, with no whole-row guess either way.
    """
    tags = fleet_tags()
    counts = {t: 0 for t in tags}
    counts["landing"] = 0
    unattributed = 0
    for row in page_rows:
        path = row["path"]
        if path in ("/", "/index.html"):
            for date, n in row["daily"].items():
                if date < ROOT_MOVED:
                    counts["il"] += n
                else:
                    counts["landing"] += n
            continue
        tag = path.lstrip("/").split("/", 1)[0]
        if tag in counts:
            counts[tag] += row["count"]
        else:
            unattributed += row["count"]
    out = [{"key": t, "count": counts[t]} for t in tags + ["landing"]]
    if unattributed:
        # Named rather than folded into a bar: these are the site's own
        # non-instance pages (privacy, traffic, sponsorship) plus anything new.
        out.append({"key": "(other pages)", "count": unattributed})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--explore", action="store_true",
                    help="print each response's shape and stop")
    ap.add_argument("--dry-run", action="store_true",
                    help="fetch and summarise, write nothing")
    args = ap.parse_args()

    tok = token()
    start, end = window()
    s, total = session(tok, start, end)
    print("window %s..%s (%d days)" % (start, end, WINDOW_DAYS))
    if args.explore:
        explore(s, total, start, end)
        return

    data = collect(s, total, start, end)

    # The period total and the daily series are two different counts of the
    # same period — GoatCounter deduplicates visits for the first and does not
    # for the second — so they are both kept and neither is derived from the
    # other. What must hold is that the series is not EMPTY.
    if not data["daily"] or data["pageviews"] < MIN_PAGEVIEWS:
        sys.exit("refusing to write: %d pageviews across %d days in %s..%s. "
                 "That is a revoked token or a changed dashboard, not a quiet "
                 "week." % (data["pageviews"], len(data["daily"]), start, end))

    # After the full window, because it changes the session's period.
    data["windows"] = preset_windows(s, end)

    attributed = sum(r["count"] for r in data["instances"])
    print("%d pageviews, %d events over %d days; instances sum to %d"
          % (data["pageviews"], data["events"], len(data["daily"]), attributed))
    for r in data["instances"]:
        print("  %-14s %d" % (r["key"], r["count"]))

    out = {
        "_comment": ("Generated by scripts/goatcounter_fetch.py from the "
                     "districtry.goatcounter.com dashboard. The window is a "
                     "rolling two months ending on the last full day. 'total' "
                     "is GoatCounter's deduplicated period total, which is "
                     "NOT the sum of the daily series. 'windows' holds the same "
                     "lists read for the last 7, 14 and 30 days."),
        "fetched": datetime.datetime.now(datetime.timezone.utc)
                           .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "site": SITE,
        "window": {"start": start, "end": end, "days": WINDOW_DAYS},
    }
    out.update(data)
    if args.dry_run:
        print("dry run — nothing written")
        return
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, sort_keys=False)
        f.write("\n")
    print("wrote %s" % os.path.relpath(OUT))


if __name__ == "__main__":
    main()
