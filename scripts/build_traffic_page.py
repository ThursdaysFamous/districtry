#!/usr/bin/env python3
"""Rewrite traffic.html's data block from the three committed data files.

WHY THIS IS A SCRIPT. The report was rebuilt by hand: a session read the three
JSON files, worked out each figure, and spliced five declarations into the page.
That is half an hour of careful work every day, and every one of those days is a
chance to paste a number into the wrong array. Everything between the
TRAFFIC-DATA markers is now derived, so the daily refresh is one command and the
only judgment left is the PROSE, which is where judgment belongs.

IT ALSO WRITES THE data-stat FALLBACKS, added 2026-09-15. Every figure in the
prose sits in a `<span data-stat="key">` whose text the page replaces at load
from the same data block. The literal inside it is what a CRAWLER reads and
what a reader with no JavaScript sees, and it was hand-typed once and never
again. Measured that day, traffic.html carried THREE different windows: the
header span said "July 10 – August 29, 2026 · 51 days", the note's said
"July 14 – September 13, 2026, 62 days", and the data block said 15 July to
14 September. Two of the three were stale and all three disagreed, on a page
whose subject is measurement.

So the fallbacks for the figures this already derives are written here, and two
spans carrying the same key must carry the same text — which is the check that
would have caught the two windows, since they are both `data-stat="range"`.
A key this cannot compute keeps its literal and is PRINTED on every run, so the
remaining hand-typed ones are visible rather than assumed current.

WHAT IT DOES NOT DO, deliberately:

  * It does not touch a word of prose. The page's sentences make claims the data
    can outlive — "ward leads", "the four days ran", the 2026-08-24 root-split
    caveat — and a generator that rewrote those would be inventing them. Read
    the reconciliation this prints, then read the page.
  * It is NOT a CI gate. The three fetch workflows commit their files on their
    own schedule, so between a fetch and the next rebuild the page and the data
    legitimately disagree; a --check in CI would fail main every day for hours.
    --check exists for a person about to rebuild, to see what would move.

THE TWO TOTALS ARE BOTH PRINTED AND NEITHER IS DERIVED FROM THE OTHER.
GoatCounter's js-total-utc is what the bar widgets are a share of — the browser,
system and location rows sum to it exactly — while the daily series sums lower.
Both count the same period, this project does not know what the difference is,
and an earlier note explaining it as deduplication was wrong in the direction it
predicted (that would make the total SMALLER; it is larger).
"""

import argparse
import datetime
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# The day the Illinois app moved off `/`. The page annotates the peak with it
# only while the peak IS that day, so the literal here must agree with the
# REBRAND constant traffic.html's own script carries.
REBRAND = "2026-08-24"
PAGE = os.path.join(ROOT, "traffic.html")
BEGIN = "  /* ==== TRAFFIC-DATA:BEGIN ==== */"
END = "  /* ==== TRAFFIC-DATA:END ==== */"

# Display names. The instance tags come from metros.json so a new state appears
# by itself; these spell each one the way the page's bars already read.
INSTANCE_NAMES = {"il": "Illinois", "ny": "New York", "ca": "San Francisco",
                  "wi": "Wisconsin", "ia": "Iowa", "mi": "Michigan",
                  "landing": "Fleet landing"}
# GoatCounter publishes a referrer's HOST; these are the names a reader knows.
# A host with no entry ships exactly as GoatCounter spells it.
REF_NAMES = {"(unknown)": "Direct / unknown", "duckduckgo.com": "DuckDuckGo",
             "go.bsky.app": "Bluesky", "www.bing.com": "Bing",
             "bsky.app": "Bluesky", "www.google.com": "Google",
             "search.brave.com": "Brave", "www.reddit.com": "Reddit"}
LAYER_NAMES = {"ward": "Ward", "school-board": "School board",
               "congress": "Congress", "il-house": "IL House",
               "il-senate": "IL Senate", "county-board": "County board",
               "ward-precinct": "Ward precinct",
               "police-district": "Police district",
               "ccpsa-district-council": "Police council",
               "school-district": "School district", "county": "County",
               # The three tilings the app registers separately. Only the
               # unified one has reached the top ten so far, and it did so
               # unnamed: an id with no entry ships as the raw id, so the bar
               # read "school-district-unified" beside "School board".
               "school-district-unified": "School district (unified)",
               "school-district-elementary": "School district (elementary)",
               "school-district-secondary": "School district (high)",
               "judicial-subcircuit": "Judicial subcircuit",
               "county-precinct": "County precinct",
               "fire-district": "Fire district", "park-district": "Park district",
               "library-district": "Library district",
               "il-supreme-court": "IL Supreme Court", "ccbr": "Board of Review",
               "municipality": "Municipality", "township": "Township",
               "zip": "ZIP code", "school-site": "School site",
               "cps-elementary": "CPS elementary", "cps-high": "CPS high",
               "police-beat": "Police beat", "fire-station": "Fire station",
               "police-station": "Police station", "ssa": "Special service area",
               "senate": "State Senate", "house": "State House",
               "council": "City council", "community-board": "Community board",
               "supervisor-district": "Supervisor district"}
# The day the Illinois app moved from "/" to "/il/" and the landing page took
# the root path. Root pageviews are split at it, one day at a time.
ROOT_MOVED = "2026-08-24"
MONTH = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
         "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def fail(msg):
    sys.exit("build-traffic-page: FAIL — %s" % msg)


def load(name):
    path = os.path.join(ROOT, "data", name)
    if not os.path.exists(path):
        fail("%s is missing. Its workflow has not run, or has not committed."
             % os.path.relpath(path, ROOT))
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def label(iso):
    y, m, d = (int(x) for x in iso.split("-"))
    return "%s %d" % (MONTH[m - 1], d)


def long_label(iso):
    return datetime.date.fromisoformat(iso).strftime("%B %-d")


def rows(pairs, per_line=3):
    out, line = [], []
    for name, count in pairs:
        line.append('["%s", %d]' % (name.replace('"', '\\"'), count))
        if len(line) == per_line:
            out.append(", ".join(line))
            line = []
    if line:
        out.append(", ".join(line))
    return ",\n      ".join(out)


def named(series, table):
    return [(table.get(r["key"], r["label"] or r["key"]), r["count"])
            for r in series]


def fleet_tags():
    with open(os.path.join(ROOT, "metros.json"), encoding="utf-8") as f:
        return [m["tag"] for m in json.load(f)["metros"] if m.get("tag")]


def newest_property(doc):
    """The reporting property whose first day is latest, named and measured."""
    live = [(name, p) for name, p in doc["properties"].items()
            if p["impressions"] and p.get("first_date")]
    if len(live) < 2:
        return None
    name, p = max(live, key=lambda kv: kv[1]["first_date"])
    host = name.split("//")[-1].strip("/").replace("sc-domain:", "")
    first = datetime.date.fromisoformat(p["first_date"])
    return {"host": host, "first": p["first_date"],
            # Formatted here: the page would otherwise have to parse an ISO
            # date, and every other date it prints is already a label.
            "firstLabel": first.strftime("%B %-d"),
            "clicks": p["clicks"], "impressions": p["impressions"]}


def engine(doc, start, end):
    """One search card's figures, summed across that engine's properties.

    Clipped to the window by DATE on the daily series. The per-query rows carry
    no date in either API, which is why both fetchers already window their own
    file — a wider file could not be clipped here at all.
    """
    clicks = impressions = 0
    queries, first, last = {}, None, None
    for prop in doc["properties"].values():
        for d in prop["days"]:
            if not (start <= d["key"] <= end):
                continue
            clicks += d["clicks"]
            impressions += d["impressions"]
            first = d["key"] if first is None else min(first, d["key"])
            last = d["key"] if last is None else max(last, d["key"])
        for q in prop["queries"]:
            a = queries.setdefault(q["key"], {"q": q["key"], "clicks": 0,
                                              "impressions": 0, "_pos": 0.0})
            a["clicks"] += q["clicks"]
            a["impressions"] += q["impressions"]
            # Position is weighted by the impressions it describes: an
            # unweighted mean counts a day with one impression as heavily as a
            # day with two hundred.
            a["_pos"] += (q["position"] or 0) * q["impressions"]
    top = sorted(queries.values(), key=lambda a: -a["impressions"])[:12]
    return {
        "clicks": clicks, "impressions": impressions, "queries": len(queries),
        "top": [{"q": a["q"], "clicks": a["clicks"],
                 "impressions": a["impressions"],
                 "position": round(a["_pos"] / a["impressions"], 1)
                 if a["impressions"] else 0} for a in top],
        "properties": len(doc["properties"]),
        # How many properties returned any rows at all, which is not the same
        # as how many exist. It moves: districtry.com was verified on Bing and
        # silent until 2026-09-13, and the card's sentence about that has to
        # move with it rather than being a literal somebody has to notice.
        "reporting": sum(1 for p in doc["properties"].values()
                         if p["impressions"]),
        # The property that started reporting most recently, with what it has
        # so far, so the card can say which domain carries the figures.
        "newest": newest_property(doc),
        "first": first, "last": last,
    }


def split_by_instance(gc, pageviews):
    """The per-instance bars, out of the fetcher's own instances[].

    NOT RECOMPUTED HERE, and the first draft of this script tried to: the split
    needs each pages row's OWN daily series to divide the root path at the day
    it changed hands, and goatcounter_fetch.py strips that series before
    writing (it is 62 numbers per row and nothing else reads it). Recomputed
    from the shipped file the bars came to 487 of 1,232 — every root pageview
    lost — which the reconciliation below caught. The fetcher decides the
    split; this only names the rows.
    """
    residual = 0
    named_rows = []
    for row in gc["instances"]:
        if row["key"] in INSTANCE_NAMES:
            named_rows.append((INSTANCE_NAMES[row["key"]], row["count"]))
        else:
            # The fetcher's own "(not in the pages list)" row: the dashboard's
            # pages list caps at ten, so the long tail is in the total and in
            # no bar.
            residual += row["count"]
    named_rows.sort(key=lambda r: -r[1])
    attributed = sum(n for _, n in named_rows) + residual
    if attributed != pageviews:
        fail("the instance split does not reconcile: %d pageviews in the "
             "totals widget, %d across the bars and the long tail. The "
             "fetcher writes both; they cannot disagree."
             % (pageviews, attributed))
    return named_rows, residual


def build():
    gc = load("goatcounter-traffic.json")
    gsc = load("search-performance.json")
    bing = load("bing-search-performance.json")
    start, end = gc["window"]["start"], gc["window"]["end"]

    daily = ",\n    ".join('["%s", %d, %d]' % (label(d["date"]), d["pageviews"],
                                               d["events"])
                           for d in gc["daily"])
    instances, residual = split_by_instance(gc, gc["pageviews"])
    ev = {r["path"]: r["count"] for r in gc["top_events"]}
    pg = {r["path"]: r["count"] for r in gc["pages"]}
    layers = [(LAYER_NAMES.get(r["path"][6:], r["path"][6:]), r["count"])
              for r in gc["layers"][:10]]
    daily_sum = gc["pageviews"] + gc["events"]

    block = '''%s
  /* GENERATED by scripts/build_traffic_page.py from data/goatcounter-traffic.json,
     data/search-performance.json and data/bing-search-performance.json, which
     three daily workflows commit. Do not hand-edit: rerun the script. The
     window is a ROLLING TWO MONTHS ending on the last full day — %s → %s —
     so this page no longer runs from launch and grows without bound.

     The PROSE around this block is not generated and can outlive its numbers.
     Read the script's reconciliation output, then read the page. */

  var daily = [
    %s
  ];

  /* Google Search Console. Both properties are summed: the site renamed
     mid-history and the old domain still appears in results and redirects
     across, so those are two different results for one search rather than one
     counted twice. */
  var searchData = %s;

  /* Bing Webmaster Tools, same window. `reporting` is how many of the verified
     properties returned any rows at all. */
  var bingData = %s;

  var barData = {
    instances: [
      %s
    ],
    layers: [
      %s
    ],
    refs: [
      %s
    ],
    systems: [
      %s
    ],
    browsers: [
      %s
    ],
    actions: [
      %s
    ],
    geo: [
      %s
    ],
    campaigns: [
      %s
    ],
    /* geolocate-success events; the meter is geoSuccess / Geolocations */
    geoSuccess: %d,
    /* the two Illinois SEO pages the narrative tracks, so the sentence cannot
       claim a figure the path widget has moved past */
    seo: { police: %d, school: %d },
    /* Page visits no instance bar carries: the dashboard's pages list caps at
       ten rows, so the long tail is in the pageview total and in no bar. */
    instResidual: %d
  };

  /* The two facts no arithmetic on this page can recover, so they are stated
     once and used everywhere:

       exportDate — the day the dashboard was read.
       total      — GoatCounter's own js-total-utc for the window. The browser,
                    system and location bars sum to it EXACTLY (%s), and the
                    daily columns sum to %s — %s apart, and the SIGN FLIPS day
                    to day (61 the other way on 2026-09-14), which rules out a
                    fixed offset. Both count the same period and this page does
                    not know what the difference is, so both are printed and
                    neither is derived from the other.

     EVERYTHING ELSE is computed below from `daily` and `barData`. */
  var META = { exportDate: "%s", year: %d, total: %d };
%s''' % (
        BEGIN, start, end, daily,
        json.dumps(engine(gsc, start, end), separators=(",", ":")),
        json.dumps(engine(bing, start, end), separators=(",", ":")),
        rows(instances), rows(layers),
        rows(named(gc["referrers"], REF_NAMES)),
        rows([(r["label"] or r["key"], r["count"]) for r in gc["systems"]]),
        rows([(r["label"] or r["key"], r["count"]) for r in gc["browsers"]]),
        rows([("Point selects", ev.get("select", 0)),
              ("Address searches", ev.get("address-search", 0)),
              ("Geolocations", ev.get("geolocate", 0))]),
        rows([(r["label"] or r["key"], r["count"]) for r in gc["locations"]]),
        rows([(r["label"] or r["key"], r["count"]) for r in gc["campaigns"]], 2),
        ev.get("geolocate-success", 0),
        pg.get("/il/police-district.html", 0), pg.get("/il/school-board.html", 0),
        residual,
        "{:,}".format(gc["total"]), "{:,}".format(daily_sum),
        "{:,}".format(abs(gc["total"] - daily_sum)),
        datetime.date.fromisoformat(gc["fetched"][:10]).strftime("%B %-d, %Y"),
        int(start[:4]), gc["total"], END)

    # The fallbacks a crawler reads. Only the keys this script already derives;
    # everything else keeps its literal and is printed below.
    fallbacks = {
        # LONG month names, matching the page's own longMonth(): a literal in a
        # different format from what the script writes makes the text visibly
        # change on load, which is its own small lie about the measurement.
        "range": "%s – %s, %d" % (long_label(start), long_label(end), int(end[:4])),
        "days": str(len(gc["daily"])),
        "total": "{:,}".format(gc["total"]),
        "pageviews": "{:,}".format(gc["pageviews"]),
        "dailySum": "{:,}".format(daily_sum),
        "dailyGap": "{:,}".format(abs(gc["total"] - daily_sum)),
        "exportDate": datetime.date.fromisoformat(
            gc["fetched"][:10]).strftime("%B %-d, %Y"),
    }
    # The peak day, computed the way the page computes it: the daily row with
    # the largest pageviews + events. Its two spans disagreed until this ran —
    # one said "August 24" and the other "Monday, Aug 24 — rebrand day", and
    # the page overwrote both with the second, so only a crawler saw the split.
    peak = max(gc["daily"], key=lambda d: d["pageviews"] + d["events"])
    peak_date = datetime.date.fromisoformat(peak["date"])
    fallbacks["peak"] = "{:,}".format(peak["pageviews"] + peak["events"])
    # The location bar's first row is the United States, and the tile beside it
    # states that count against the window total. Both are in the data block.
    us = gc["locations"][0]
    fallbacks["usCount"] = "{:,}".format(us["count"])
    fallbacks["usPct"] = "%d%%" % round(100.0 * us["count"] / gc["total"])
    fallbacks["perDay"] = str(round(gc["pageviews"] / len(gc["daily"])))
    fallbacks["peakLabel"] = "%s, %s%s" % (
        peak_date.strftime("%A"), label(peak["date"]),
        " \u2014 rebrand day" if peak["date"] == REBRAND else "")
    return block, gc, instances, residual, daily_sum, fallbacks


SPAN_RE = re.compile(r'(<span data-stat="([A-Za-z]+)">)([^<]*)(</span>)')


def apply_fallbacks(page, fallbacks):
    """Rewrite each data-stat span's literal, and hold duplicates to one text.

    The duplicate check is the one that matters. Two spans can name the same
    key and carry different words, and the page looks right in a browser
    because the script overwrites both — so the disagreement is visible only to
    a crawler, which is the reader this page's own prose is least written for.
    """
    seen, unwritten = {}, {}

    def one(m):
        open_tag, key, text, close = m.groups()
        if key in fallbacks:
            text = fallbacks[key]
        else:
            unwritten.setdefault(key, set()).add(text)
        seen.setdefault(key, set()).add(text)
        return open_tag + text + close

    page = SPAN_RE.sub(one, page)
    clashes = sorted(k for k, v in seen.items() if len(v) > 1)
    if clashes:
        k = clashes[0]
        fail("%d data-stat key(s) carry more than one fallback, starting with "
             "%r: %s. A reader with JavaScript sees one number and a crawler "
             "sees two different ones."
             % (len(clashes), k, " / ".join(sorted("%r" % t for t in seen[k]))))
    return page, unwritten


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="report what would change and write nothing")
    args = ap.parse_args()

    block, gc, instances, residual, daily_sum, fallbacks = build()
    page = open(PAGE, encoding="utf-8").read()
    if BEGIN not in page or END not in page:
        fail("traffic.html carries no TRAFFIC-DATA markers. Add them around the "
             "daily/searchData/bingData/barData/META declarations.")
    head, rest = page.split(BEGIN, 1)
    _, tail = rest.split(END, 1)
    updated, unwritten = apply_fallbacks(head + block + tail, fallbacks)

    print("window %s → %s (%d days), read %s"
          % (gc["window"]["start"], gc["window"]["end"], len(gc["daily"]),
             gc["fetched"]))
    print("%d pageviews + %d events = %d; GoatCounter's own total %d, %d apart"
          % (gc["pageviews"], gc["events"], daily_sum, gc["total"],
             gc["total"] - daily_sum))
    for name, count in instances:
        print("  %-16s %d" % (name, count))
    print("  %-16s %d (long tail, in no bar)" % ("(not listed)", residual))
    print("  %d data-stat span(s) written from the data; %d key(s) keep a "
          "hand-typed fallback a crawler reads: %s"
          % (len(fallbacks), len(unwritten), ", ".join(sorted(unwritten)) or "none"))

    if args.check:
        print("build-traffic-page: %s"
              % ("current" if updated == page else "WOULD CHANGE — rerun "
                 "without --check"))
        return
    if updated == page:
        print("build-traffic-page: OK — no change")
        return
    with open(PAGE, "w", encoding="utf-8") as f:
        f.write(updated)
    print("build-traffic-page: wrote %s — now READ THE PROSE, which this "
          "script does not touch" % os.path.relpath(PAGE, ROOT))


if __name__ == "__main__":
    main()
