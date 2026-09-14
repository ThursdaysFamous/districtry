#!/usr/bin/env python3
"""Fetch Bing Webmaster Tools search performance into data/bing-search-performance.json.

The Google half of this pair is scripts/gsc_fetch.py and this follows it
deliberately: the credential is a repo secret, an Actions secret exists only
inside a job, so the fetch runs in the workflow and commits its result, and the
committed JSON is the handoff to whatever draws the chart.

WHAT BING'S API DOES NOT HAVE, because it shapes everything below.

  * NO DATE RANGE. Not one of the stats methods takes a start or end date
    (learn.microsoft.com/en-us/dotnet/api/microsoft.bing.webmaster.api.interfaces.iwebmasterapi).
    You get whatever history Bing decides to return, so the window is applied
    HERE, and the full range that came back is recorded beside it — the
    retention is stated in no Microsoft document, and Bing's own 2024-10-16
    post extending the UI to 16 months says nothing about the API. Measure it,
    do not hardcode it.
  * NO BULK METHOD. One call per site, and per-query detail is one call per
    query, which is why only the site-wide series and the flat query and page
    lists are taken.
  * NO 'd'-LESS SUCCESS. Every success is {"d": [...]}; an error is a BARE
    object {"ErrorCode":3,"Message":"InvalidApiKey"} with HTTP 400, so a
    missing "d" is treated as a failure rather than as no data.

SITES ARE DISCOVERED, NEVER CONSTRUCTED. GetUserSites returns each property's
Url exactly as it was verified, and Bing matches on it: a constructed
"https://districtry.com" against a property verified as "http://districtry.com"
returns an empty list rather than an error. The same rule gsc_fetch.py follows,
for the same reason, and here it also covers the rename — chidistricts.com and
districtry.com are separate properties if both are verified.

DATES COME BACK AS /Date(1316156400000-0700)/ — milliseconds since the epoch
plus the local offset Bing meant. The milliseconds are absolute; the offset
only says which local midnight, so the day is read off the offset local time.

NOTHING PER-PERSON IS COLLECTED. Rows are aggregate query, page and day counts.
"""

import datetime
import json
import os
import re
import sys

import requests

API = "https://ssl.bing.com/webmaster/api.svc/json"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "data", "bing-search-performance.json")

# Two months, in days, matching scripts/goatcounter_fetch.py. Bing decides how
# much history to hand over; this decides how much of it is published.
WINDOW_DAYS = 62

# A property returning nothing is usually a revoked key or an unverified site
# rather than a quiet week, and writing that would silently empty the card.
MIN_IMPRESSIONS = 1

TIMEOUT = 120
# Microsoft's samples all show an offset — /Date(1316156400000-0700)/ — and
# the live API sends none: measured 2026-09-14, every row came back as
# /Date(1784073600000)/, a bare UTC midnight, which the offset-required form
# refused. The offset is optional here and absent means UTC.
DATE_RE = re.compile(r"^/Date\((-?\d+)(?:([+-]\d{4}))?\)/$")


def key():
    raw = os.environ.get("BING_API_KEY", "").strip()
    if not raw:
        sys.exit("BING_API_KEY is unset — this must run where the secret is "
                 "mounted (see .github/workflows/update-bing-performance.yml).")
    return raw


def call(method, apikey, **params):
    """One JSON GET. Returns the "d" list, or exits naming what came back."""
    params = dict(params, apikey=apikey)
    r = requests.get("%s/%s" % (API, method), params=params, timeout=TIMEOUT)
    try:
        body = r.json()
    except ValueError:
        sys.exit("%s: HTTP %d and a non-JSON body — %s"
                 % (method, r.status_code, r.text[:300]))
    if r.status_code != 200 or "d" not in body:
        # NEVER echo params here: apikey is in them.
        sys.exit("%s: HTTP %d — %s" % (method, r.status_code,
                                       json.dumps(body)[:300]))
    return body["d"]


def day(value):
    """'/Date(1316156400000-0700)/' -> '2011-09-16'.

    The offset is what says which local day Bing meant; reading the epoch
    milliseconds as UTC moves a row to the wrong day for anything west of
    Greenwich, which is every US property.
    """
    m = DATE_RE.match(value or "")
    if not m:
        sys.exit("unparseable date from Bing: %r" % (value,))
    ms, off = int(m.group(1)), m.group(2)
    moment = datetime.datetime.fromtimestamp(ms / 1000.0, datetime.timezone.utc)
    if off:
        sign = 1 if off[0] == "+" else -1
        moment += sign * datetime.timedelta(hours=int(off[1:3]),
                                            minutes=int(off[3:5]))
    return moment.date().isoformat()


def window():
    end = datetime.date.today() - datetime.timedelta(days=1)
    return (end - datetime.timedelta(days=WINDOW_DAYS - 1)).isoformat(), end.isoformat()


def rows(raw, label_field="Query"):
    """Flatten one stats list, keeping the fields Bing actually defines."""
    out = []
    for r in raw:
        out.append({
            "key": r.get(label_field),
            "date": day(r["Date"]) if r.get("Date") else None,
            "clicks": r.get("Clicks", 0),
            "impressions": r.get("Impressions", 0),
            "avg_click_position": r.get("AvgClickPosition"),
            "avg_impression_position": r.get("AvgImpressionPosition"),
        })
    return out


def collapse(flat):
    """Sum a per-day-per-key list down to one row per key.

    GetQueryStats and GetPageStats return a row per key PER DAY, so a top-list
    built straight off them ranks a query that had one good day above one that
    ran steadily. The averaged positions are weighted by the impressions they
    describe, because an unweighted mean of daily positions counts a day with
    one impression as heavily as a day with two hundred.
    """
    acc = {}
    for r in flat:
        a = acc.setdefault(r["key"], {"key": r["key"], "clicks": 0,
                                      "impressions": 0, "_pos": 0.0,
                                      "first": r["date"], "last": r["date"]})
        a["clicks"] += r["clicks"]
        a["impressions"] += r["impressions"]
        if r["avg_impression_position"] is not None:
            a["_pos"] += r["avg_impression_position"] * r["impressions"]
        if r["date"]:
            a["first"] = min(a["first"] or r["date"], r["date"])
            a["last"] = max(a["last"] or r["date"], r["date"])
    out = []
    for a in acc.values():
        imp = a["impressions"]
        out.append({"key": a["key"], "clicks": a["clicks"], "impressions": imp,
                    "position": round(a["_pos"] / imp, 2) if imp else None,
                    "first": a["first"], "last": a["last"]})
    return sorted(out, key=lambda x: -x["impressions"])


def main():
    apikey = key()
    start, end = window()

    sites = call("GetUserSites", apikey)
    # Print the whole list, verified or not. The rename means two properties
    # are expected and a missing one is a fact about Bing Webmaster Tools
    # rather than about this script, so it has to be visible in the log.
    for site in sites:
        print("property %s — verified=%s"
              % (site.get("Url"), site.get("IsVerified")))
    verified = [s["Url"] for s in sites if s.get("IsVerified")]
    if not verified:
        sys.exit("no verified Bing Webmaster properties for this key (%d "
                 "site(s) returned, none verified). Verify the site in Bing "
                 "Webmaster Tools — the API key is per user, not per site."
                 % len(sites))

    out = {
        "_comment": ("Generated by scripts/bing_fetch.py from the Bing "
                     "Webmaster Tools JSON API. No stats method takes a date "
                     "range, so 'window' is applied here and 'returned' "
                     "records the full range Bing handed over; properties are "
                     "discovered per run, not hardcoded."),
        "fetched": datetime.datetime.now(datetime.timezone.utc)
                           .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window": {"start": start, "end": end, "days": WINDOW_DAYS},
        "properties": {},
    }
    total_impressions = 0

    for site in sorted(verified):
        print("fetching %s" % site)
        traffic = rows(call("GetRankAndTrafficStats", apikey, siteUrl=site), "Date")
        queries = rows(call("GetQueryStats", apikey, siteUrl=site), "Query")
        # GetPageStats returns the same QueryStats class, with the page URL in
        # the Query field. Microsoft's own XML and JSON samples disagree about
        # that field's contents; the XML one (<Query>PageURL</Query>) is right.
        pages = rows(call("GetPageStats", apikey, siteUrl=site), "Query")

        all_dates = sorted(r["date"] for r in traffic if r["date"])
        inside = [r for r in traffic if r["date"] and start <= r["date"] <= end]
        days = [{"key": r["date"], "clicks": r["clicks"],
                 "impressions": r["impressions"]} for r in sorted(
                     inside, key=lambda r: r["date"])]
        clicks = sum(r["clicks"] for r in days)
        impressions = sum(r["impressions"] for r in days)
        total_impressions += impressions

        print("  returned %s..%s (%d days); in window %s..%s — %d clicks, "
              "%d impressions"
              % (all_dates[0] if all_dates else "-",
                 all_dates[-1] if all_dates else "-", len(all_dates),
                 days[0]["key"] if days else "-", days[-1]["key"] if days else "-",
                 clicks, impressions))

        out["properties"][site] = {
            "returned": {"first": all_dates[0] if all_dates else None,
                         "last": all_dates[-1] if all_dates else None,
                         "days": len(all_dates)},
            "first_date": days[0]["key"] if days else None,
            "last_date": days[-1]["key"] if days else None,
            "clicks": clicks,
            "impressions": impressions,
            "days": days,
            # Ranked by impressions, not clicks: the click column is mostly
            # zeroes at this traffic level, so a clicks sort returns one real
            # row and then ties. Same reasoning as gsc_fetch.py.
            "queries": collapse([r for r in queries
                                 if r["date"] and start <= r["date"] <= end])[:500],
            "pages": collapse([r for r in pages
                               if r["date"] and start <= r["date"] <= end]),
        }

    if total_impressions < MIN_IMPRESSIONS:
        sys.exit("refusing to write: %d impressions across %d verified "
                 "property(ies) in %s..%s. That is a revoked key or an API "
                 "change, not a quiet week."
                 % (total_impressions, len(verified), start, end))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, sort_keys=False)
        f.write("\n")
    print("wrote %s — %d property(ies), %d impressions"
          % (os.path.relpath(OUT), len(verified), total_impressions))


if __name__ == "__main__":
    main()
