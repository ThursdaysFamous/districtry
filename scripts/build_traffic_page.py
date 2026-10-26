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
# The day the layer event started carrying the instance tag (engine
# overlay-cards). Before it, `layer/<id>` pooled every app registering that id;
# after it, `layer/<tag>/<id>`. A historical fact that never moves, like
# REBRAND above, and the page needs it to date its own partial attribution.
LAYER_SPLIT = "2026-09-29"
PAGE = os.path.join(ROOT, "traffic.html")
BEGIN = "  /* ==== TRAFFIC-DATA:BEGIN ==== */"
END = "  /* ==== TRAFFIC-DATA:END ==== */"

# Display names, one per served instance plus the fleet landing page. THIS
# TABLE IS HAND-KEPT AND ITS OWN COMMENT USED TO DENY IT — it read "the instance
# tags come from metros.json so a new state appears by itself", which is true of
# the layer split and false here: a tag with no entry falls into the "(not in
# the pages list)" residual, so the state's visits would land in the long tail
# rather than in a bar of its own, with the reconciliation still balancing and
# every gate green. Minnesota went live on 2026-09-30 with no entry, which is
# how this was found. check_instance_names() below now FAILS on a metros.json
# tag this table does not spell.
INSTANCE_NAMES = {"il": "Illinois", "ny": "New York", "ca": "San Francisco",
                  "wi": "Wisconsin", "ia": "Iowa", "mi": "Michigan",
                  "mn": "Minnesota", "ky": "Kentucky", "in": "Indiana",
                  "nc": "North Carolina", "ok": "Oklahoma",
                  "sc": "South Carolina",
                  "tn": "Tennessee",
                  "ar": "Arkansas",
                  "ms": "Mississippi",
                  "la": "Louisiana",
                  "landing": "Front page"}
# The day each instance was first LISTED on the front door, measured once with
#   git log --reverse --format=%cs -S'"tag": "<tag>"' -- metros.json
# and recorded here rather than re-read, so this build needs no git and cannot
# be wrong in a shallow clone (the sitemap lesson). These are historical facts
# that never move, like REBRAND and LAYER_SPLIT above. Used for ONE comparison:
# whether an instance was listed at all during the window, which is what tells a
# bar reading zero because its visits are in the capped list's long tail from one
# reading zero because the app was not being served. Illinois, New York and San
# Francisco were all served before they were listed — the tag key itself only
# arrived with the path move — so these dates are a LOWER BOUND on being served,
# which is all the comparison needs. check_instance_names() fails on a tag with
# no entry.
FLEET_LISTED = {"il": "2026-08-24", "ny": "2026-08-24", "ca": "2026-08-24",
                "wi": "2026-08-25", "ia": "2026-08-27", "mi": "2026-09-03",
                "mn": "2026-09-30", "ky": "2026-09-30",
                "in": "2026-10-07", "nc": "2026-10-09",
                "ok": "2026-10-10", "sc": "2026-10-13",
                "tn": "2026-10-13", "ar": "2026-10-15",
                "ms": "2026-10-16", "la": "2026-10-21"}
# GoatCounter publishes a referrer's HOST; these are the names a reader knows.
# A host with no entry ships exactly as GoatCounter spells it.
REF_NAMES = {"(unknown)": "Direct / unknown", "duckduckgo.com": "DuckDuckGo",
             "go.bsky.app": "Bluesky", "www.bing.com": "Bing",
             "bsky.app": "Bluesky", "www.google.com": "Google",
             "search.brave.com": "Brave", "www.reddit.com": "Reddit",
             # The Play app opens its start page as /app/?ref=play.
             "play": "Android app"}
# The per-day source chart's groups. A referrer key in none of these, other
# than "(unknown)", counts as "Other sites", which is where a smaller search
# engine (Brave, Ecosia) lands too; the page's note says so.
DAY_REF_GROUPS = [
    ("Google", {"Google", "www.google.com", "google.com"}),
    ("DuckDuckGo", {"duckduckgo.com", "noai.duckduckgo.com", "DuckDuckGo"}),
    ("Bing", {"www.bing.com", "bing.com", "cn.bing.com", "Bing"}),
    ("Yahoo", {"Yahoo", "search.yahoo.com", "yahoo.com"}),
]
NO_SOURCE = "(unknown)"
LAYER_NAMES = {"ward": "Ward", "school-board": "School board",
               "congress": "Congress", "il-house": "IL House",
               "il-senate": "IL Senate", "county-board": "County board",
               "ward-precinct": "Ward precinct",
               "police-district": "Police district",
               "ccpsa-district-council": "Police council",
               "school-district": "School district", "county": "County",
               # Every state app except Illinois, New York and San Francisco
               # registers its U.S. House layer as "us-house"; it reached the
               # top ten on 2026-10-18 and drew as the raw id.
               "us-house": "U.S. House",
               # The three tilings the app registers separately. Only the
               # unified one has reached the top ten so far, and it did so
               # unnamed: an id with no entry ships as the raw id, so the bar
               # read "school-district-unified" beside "School board".
               "school-district-unified": "School district (unified)",
               "school-district-elementary": "School district (elementary)",
               "school-district-secondary": "School district (high)",
               # Reached the 7-day top ten on 2026-10-26, a few days after the
               # ZIP search started turning the layer on, and drew as the raw id.
               "zip-code": "ZIP code",
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
# The day the search boxes started counting the map links they read
# (`map-link-read/`, engine geocoder-search countLinkRead).
MAP_LINKS_FROM = "2026-10-17"
# What each map-link outcome means to a reader of this page. `to-<tag>` is the
# front page opening an app and `failed-<why>` a short link the lookup could
# not read; both are grouped below rather than listed here per value.
MAP_LINK_OUTCOMES = {"point": "Position in link",
                     "found": "Address found",
                     "pin": "House pinned",
                     "street": "Street only",
                     "name": "By place name",
                     "other-state": "Another state",
                     "uncovered": "State not covered",
                     "district": "District name",
                     "none": "Nothing matched",
                     "unreadable": "No place in link",
                     "search-failed": "Search failed"}
# The bar column is 112px, so every label here is short enough to fit it.
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


def check_instance_names():
    """Every served instance must have a display name, or it loses its bar.

    The failure is silent without this: split_by_instance() puts an unnamed tag
    in the residual, which reconciles against the totals widget exactly as a
    named one does, so the page simply stops drawing that state.
    """
    tags = fleet_tags()
    missing = [t for t in tags if t not in INSTANCE_NAMES]
    if missing:
        fail("metros.json serves %s, which INSTANCE_NAMES does not spell, so "
             "those visits would go in the long tail instead of a bar. Add a "
             "display name for each." % ", ".join(missing))
    undated = [t for t in tags if t not in FLEET_LISTED]
    if undated:
        fail("metros.json serves %s, which FLEET_LISTED does not date, so the "
             "page cannot tell a bar reading zero because its visits are in "
             "the long tail from one reading zero because the app was not "
             "served yet. Measure each with git log --reverse --format=%%cs "
             "-S'\"tag\": \"<tag>\"' -- metros.json." % ", ".join(undated))


def not_listed_yet(window_end):
    """Display names of instances listed on the front door only after the window.

    A bar reading zero has two causes and the page must not conflate them: the
    dashboard's pages list caps at ten rows, so a served app's visits can sit in
    the long tail, but an app that was not being served recorded nothing at all
    and its visits are nowhere. `listed_partway` adds a third FACT about the
    same bars rather than a third cause.
    """
    return [INSTANCE_NAMES[t] for t in fleet_tags()
            if FLEET_LISTED[t] > window_end]


def listed_partway(window_start, window_end):
    """Display name -> days served, for instances listed INSIDE the window.

    MEASURED RATHER THAN DESCRIBED, because the window rolls and which apps are
    in this class changes on its own. Minnesota and Kentucky both went live on
    2026-09-30, the last day of the window read on 2026-10-01, so each had ONE
    day in a 62-day window -- and the note written the day before said
    Minnesota "went live after this window ended", which was true for one day
    and false the next.

    THIS IS DAYS LISTED, NEVER DAYS SERVED, and the difference is why the page
    adds the figure beside the long-tail sentence instead of in place of it. The
    landing page itself only began on 24 August, so for the apps that predate it
    this date records when the front door appeared and says nothing about when
    the app did. A first draft used it as a rival explanation and moved San
    Francisco and Michigan out of the long-tail sentence that is still the right
    one for them.
    """
    out = {}
    for t in fleet_tags():
        listed = FLEET_LISTED[t]
        if window_start < listed <= window_end:
            days = ((datetime.date.fromisoformat(window_end)
                     - datetime.date.fromisoformat(listed)).days + 1)
            out[INSTANCE_NAMES[t]] = days
    return out


def layer_scope(drawn):
    """Which of the DRAWN layer ids belong to one app and which SUM across.

    The layer event is `trackEvent("layer/" + mod.id)` (engine overlay-cards),
    so two instances registering the same layer id report into ONE row and this
    page cannot separate them. Note 4 used to LIST the unambiguous ids by hand
    -- `ward` = Illinois, `council` = New York, `supervisor-district` = San
    Francisco -- and `ward` was NEVER one of them. Wisconsin registered a layer
    with that id on 2026-08-25 (ee880505, #526, "Wisconsin's wards get their
    card"), the same day Wisconsin went live, and the caveat naming ward as
    Illinois-only was written on 2026-09-09 (5ebecb67, #825) -- fifteen days
    AFTER. It was false on the day it was written rather than a claim that went
    stale, and it stood for twenty days until 2026-09-29. A hand-kept list of
    which ids are single-instance is exactly the claim nothing was comparing
    against the worksheets that decide it.

    THE CORRECTION ABOVE REPLACES "STOPPED BEING ONE on 2026-09-08", which this
    docstring and two commit messages said first, and that wrong date came out
    of a SHALLOW CLONE. `git log -S'"id": "ward"' -- wi/metro-worksheet.json`
    answered 1d668f8 (2026-09-08) because 1d668f8 was THIS clone's shallow
    boundary, and at a boundary the first commit appears to create every file
    -- it showed 2,702 insertions into a worksheet it does not touch at all on
    full history. The manager session caught it from a clone whose boundary was
    a different commit six days earlier, and read ITS boundary as the earliest
    possible date in turn; the two readings disagreeing is what proved neither
    was reading history. `git fetch --unshallow` first, then date anything.

    So the ownership is READ from every instance's own `layers[]`, the same list
    that drives EXPECT_LAYER_IDS, discovered through fleet_tags() so a new
    state is covered by being registered. Measured 2026-09-29, SIX of the ten
    drawn ids are shared and four are not, which is why the prose names them
    rather than characterising them.

    A drawn id in NO worksheet is reported as unattributed rather than assumed
    unambiguous: a retired layer's events stay in a two-month window long after
    its last toggle, and calling that Illinois-only would be a guess.
    """
    owners = {}
    for tag in fleet_tags():
        path = os.path.join(ROOT, tag, "metro-worksheet.json")
        if not os.path.exists(path):
            # Illinois's worksheet is the repo-root one; it has no il/ copy.
            path = os.path.join(ROOT, "metro-worksheet.json")
        with open(path, encoding="utf-8") as f:
            for layer in json.load(f).get("layers", []):
                owners.setdefault(layer["id"], []).append(tag)
    scope = {}
    for lid in drawn:
        tags = owners.get(lid)
        scope[LAYER_NAMES.get(lid, lid)] = (
            [INSTANCE_NAMES.get(t, t) for t in tags] if tags else None)
    return scope


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


def engine(doc, start, end, key=None):
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
        # A shorter window's queries were asked for over that window; the
        # property's own list is the full window's.
        qs = (prop.get("windows", {}).get(key, {}).get("queries", [])
              if key else prop["queries"])
        for q in qs:
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


def map_link_summary(gc):
    """The map-link rows as the page draws them: three bar groups and a
    summary the lead sentence reads. Fails on a row whose path is not the
    event's six parts, because a row this cannot read would otherwise drop out
    of every total without a word."""
    sources, results, places = {}, {}, {}
    total = short = retried = opened = failed = 0
    for r in gc.get("map_links", []):
        parts = r["path"].split("/")
        if len(parts) != 6 or parts[0] != "map-link-read":
            fail("map-link row %r is not map-link-read/<tag>/<source>/<form>/<via>/<outcome>"
                 % r["path"])
        _, tag, source, form, via, outcome = parts
        n = r["count"]
        total += n
        src = {"google": "Google Maps", "apple": "Apple Maps"}.get(source, source)
        sources[src] = sources.get(src, 0) + n
        if form.startswith("short"):
            short += n
        if form == "short-retried":
            retried += n
        if via == "opened":
            opened += n
        if outcome.startswith("failed-"):
            failed += n
            what = "Short link failed"
        elif outcome.startswith("to-"):
            what = "Sent to a state"
        else:
            what = MAP_LINK_OUTCOMES.get(outcome, outcome)
        results[what] = results.get(what, 0) + n
        where = "Front page" if tag == "front" else INSTANCE_NAMES.get(tag, tag)
        places[where] = places.get(where, 0) + n
    ranked = lambda d: sorted(d.items(), key=lambda kv: (-kv[1], kv[0]))
    return ranked(sources), ranked(results), ranked(places), {
        "total": total, "short": short, "retried": retried, "opened": opened,
        "failed": failed, "cut": bool(gc.get("map_links_cut")),
        "from": long_label(MAP_LINKS_FROM),
        "measured": "map_links" in gc}


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
            # "(other pages)": the site's own pages that belong to no app, and
            # "(not in the pages list)" when the fetcher could not read the
            # list to its end. Both are in the total and in no bar.
            residual += row["count"]
    named_rows.sort(key=lambda r: -r[1])
    attributed = sum(n for _, n in named_rows) + residual
    if attributed != pageviews:
        fail("the instance split does not reconcile: %d pageviews in the "
             "totals widget, %d across the bars and the long tail. The "
             "fetcher writes both; they cannot disagree."
             % (pageviews, attributed))
    return named_rows, residual


def day_refs(gc):
    """One row per fetched day: [label, google, ddg, bing, yahoo, other,
    no-source, cut-short].

    A file fetched before the per-day lists existed has no
    `daily_referrers`, and the page then hides the section rather than
    drawing a chart of zeroes, which would read as "nobody arrived".

    A day whose list the dashboard cut short keeps its flag, because the
    rows it did not send are the smallest ones and would have landed in
    "Other sites": that cell is then a floor, and the page marks it.
    """
    out = []
    for d in gc.get("daily_referrers", []):
        counts = {name: 0 for name, _ in DAY_REF_GROUPS}
        other = none = 0
        for r in d["rows"]:
            for name, keys in DAY_REF_GROUPS:
                if r["key"] in keys or r["label"] in keys:
                    counts[name] += r["count"]
                    break
            else:
                if r["key"] == NO_SOURCE:
                    none += r["count"]
                else:
                    other += r["count"]
        out.append([label(d["date"])] + [counts[n] for n, _ in DAY_REF_GROUPS]
                   + [other, none, bool(d.get("more"))])
    return out


def return_visits(gc, start):
    """First and return visits to the apps for one window, or None.

    The fetcher reads them per day for the full window (`visits`, absent from
    a file fetched before 2026-10-27 and None when its own check refused the
    dashboard's answer). Each window's figure is the daily series cut to that
    window, so the totals and the per-day rows can never disagree.
    """
    v = gc.get("visits")
    if not v:
        return None
    first, ret = v["first_daily"], v["return_daily"]
    dates = [d["date"] for d in gc["daily"]] if "daily" in gc else None
    if dates is not None and not (len(first) == len(ret) == len(dates)):
        fail("visits: %d first and %d return days against %d in the daily "
             "series" % (len(first), len(ret), len(dates)))
    return {"since": long_label(v["since"]), "first": v["first"],
            "return": v["return"],
            "byApp": [[INSTANCE_NAMES.get(r["tag"], r["tag"]), r["count"]]
                      for r in v["by_app_return"]]}


def bar_data(gc, start, end):
    """barData for one window, as the page reads it, plus the instance rows
    and their residual for the reconciliation printout.

    `gc` is the whole fetched file for the full window, or one of its
    `windows` entries for a shorter one: both carry the same lists, read off
    the dashboard for their own period.
    """
    instances, residual = split_by_instance(gc, gc["pageviews"])
    ev = {r["path"]: r["count"] for r in gc["top_events"]}
    pg = {r["path"]: r["count"] for r in gc["pages"]}
    layers = [(LAYER_NAMES.get(r["path"][6:], r["path"][6:]), r["count"])
              for r in gc["layers"][:10]]
    # THE MEASURED ATTRIBUTION, beside the capability layer_scope() reads off
    # the worksheets. `layer_instances` is absent from a file fetched before
    # 2026-09-29 and empty on the first runs after it, so both cases degrade to
    # "nothing attributed yet" rather than to a missing key.
    attributed = {}
    for r in gc.get("layer_instances", []):
        attributed.setdefault(r["id"], {})[r["tag"]] = r["count"]
    drawn_totals = {r["path"][6:]: r["count"] for r in gc["layers"][:10]}
    split, pooled = {}, {}
    for lid, total_row in drawn_totals.items():
        name = LAYER_NAMES.get(lid, lid)
        by_tag = attributed.get(lid, {})
        got = sum(by_tag.values())
        if got > total_row:
            # The sum is wrong somewhere: a per-instance row cannot exceed the
            # id's own total, which the fetcher built by adding both shapes.
            fail("layer %s: %d attributed across %d instance(s) against a "
                 "total of %d. The fetcher sums the pooled and per-instance "
                 "shapes; these cannot disagree."
                 % (lid, got, len(by_tag), total_row))
        if by_tag:
            split[name] = {INSTANCE_NAMES.get(t, t): n
                           for t, n in sorted(by_tag.items())}
        pooled[name] = total_row - got
    ml_sources, ml_results, ml_places, ml = map_link_summary(gc)
    pairs = lambda rows_: [(r["label"] or r["key"], r["count"]) for r in rows_]
    bd = {
        "instances": instances,
        "layers": layers,
        "refs": named(gc["referrers"], REF_NAMES),
        "systems": pairs(gc["systems"]),
        "browsers": pairs(gc["browsers"]),
        "actions": [("Points chosen", ev.get("select", 0)),
                    ("Searches", ev.get("address-search", 0)),
                    ("Location requests", ev.get("geolocate", 0))],
        "geo": pairs(gc["locations"]),
        "campaigns": pairs(gc["campaigns"]),
        "mapLinkSources": ml_sources,
        "mapLinkResults": ml_results,
        "mapLinkPlaces": ml_places,
        "mapLinks": ml,
        "geoSuccess": ev.get("geolocate-success"),
        "layerScope": layer_scope([r["path"][6:] for r in gc["layers"][:10]]),
        "layerSplit": split,
        "layerPooled": pooled,
        "layerSplitFrom": long_label(LAYER_SPLIT),
        "seo": {"police": pg.get("/il/police-district.html", 0),
                "school": pg.get("/il/school-board.html", 0)},
        "instResidual": residual,
        "pagesCut": bool(gc.get("pages_truncated", True)),
        "notListedYet": not_listed_yet(end),
        "listedPartway": listed_partway(start, end),
        "visits": return_visits(gc, start),
    }
    return bd, instances, residual


def windows_block(gc, gsc, bing):
    """The shorter windows the page's timeframe buttons offer, as one object
    keyed by day count. Each carries everything the page's script reads, so
    the script renders a window exactly as it renders the full one.

    The daily series and the per-day referrer rows are the full window's cut
    to length; every list is the dashboard's own for that period. A data file
    fetched before the windows existed gives an empty object, and the page
    then offers no buttons.
    """
    end = gc["window"]["end"]
    out = {}
    for key, w in sorted(gc.get("windows", {}).items(), key=lambda kv: int(kv[0])):
        n, start = int(key), w["start"]
        days = [d for d in gc["daily"] if d["date"] >= start]
        if len(days) != n:
            fail("window %s: %d day(s) of the daily series fall on or after "
                 "%s, not %d" % (key, len(days), start, n))
        bd = bar_data(w, start, end)[0]
        out[key] = {
            "daily": [[label(d["date"]), d["pageviews"], d["events"]]
                      for d in days],
            "searchData": engine(gsc, start, end, key),
            "bingData": engine(bing, start, end, key),
            "dayRefs": [r for r in day_refs(gc)[-n:]],
            "barData": bd,
            "META": {"total": w["total"], "year": int(start[:4])},
        }
    return out


def build():
    gc = load("goatcounter-traffic.json")
    gsc = load("search-performance.json")
    bing = load("bing-search-performance.json")
    start, end = gc["window"]["start"], gc["window"]["end"]

    daily = ",\n    ".join('["%s", %d, %d]' % (label(d["date"]), d["pageviews"],
                                               d["events"])
                           for d in gc["daily"])
    check_instance_names()
    bd, instances, residual = bar_data(gc, start, end)
    daily_sum = gc["pageviews"] + gc["events"]
    compact = lambda v: json.dumps(v, separators=(",", ":"), sort_keys=True)
    wins = windows_block(gc, gsc, bing)

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

  /* Where each of the last days' visits came from, each day asked for on
     its own: [day, Google, DuckDuckGo, Bing, Yahoo, other sites, no source,
     list cut short]. Empty when the data file predates the per-day fetch. */
  var dayRefs = [
    %s
  ];

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
    /* Google Maps and Apple Maps links the search boxes read, counted since
       mapLinks.from: by which maps app, what the search showed, and which app
       or the front page read it. `measured` is false for a data file fetched
       before the count existed, which the page says rather than reading as
       zero. */
    mapLinkSources: [
      %s
    ],
    mapLinkResults: [
      %s
    ],
    mapLinkPlaces: [
      %s
    ],
    mapLinks: %s,
    /* geolocate-success events; the meter is geoSuccess / Geolocations.
       NULL, NOT ZERO, when the dashboard's ten-row events list does not carry
       the row. Absence and zero are different facts and `.get(key, 0)` made
       them the same one: on 2026-09-23 the row fell off the list and the page
       published "Geolocation succeeds 0%% of the time it is tried: 0 of 88".
       The fetch now asks for it by name, and this stays null-able because a
       row can go missing for a reason that fix does not cover. */
    geoSuccess: %s,
    /* Which apps register each DRAWN layer id, read from their own layers[].
       A list of two or more means that bar SUMS across them; null means the id
       is in no worksheet and this page will not guess whose it is. See
       layer_scope() for what a hand-kept version of this cost. */
    layerScope: %s,
    /* The MEASURED attribution: toggles the tagged event shape has recorded,
       per layer and instance, and how much of each layer's total predates it
       and stays pooled. Both are needed during the seam — layerScope says
       which ids CAN pool, these say how much actually is. */
    layerSplit: %s,
    layerPooled: %s,
    layerSplitFrom: "%s",
    /* the two Illinois SEO pages the narrative tracks, so the sentence cannot
       claim a figure the path widget has moved past */
    seo: { police: %d, school: %d },
    /* Page visits no instance bar carries. Since 2026-10-20 the fetcher reads
       the whole pages list, so these are the site's own pages that belong to
       no app (privacy, about, the Android steps page); pagesCut is true only
       when the list could not be read to its end, and then they are also the
       visits to pages the list never reached. */
    instResidual: %d,
    pagesCut: %s,
    /* Instances not LISTED on the front door for any day of this window, by
       display name. Their bars read zero because the app was not being served,
       not because the dashboard's ten-row cap hid them, and the zero-bar note
       below has to say which — a claim that their visits "sit in that long
       tail" would be false. Minnesota went live on the day after this window
       ended, which is how the distinction was found. */
    notListedYet: %s,
    /* Instances listed on the front door PARTWAY through this window, by
       display name, with the days each was LISTED -- not the days it was
       served. A zero bar for an app a reader could find for one day of this
       window is a weaker measurement than the same zero for one findable
       throughout, and the window rolls, so this is measured on every build
       rather than described in a sentence. */
    listedPartway: %s,
    /* First and return visits to the apps, counted once per browser window
       since `since` (engine install-app, visit/first and visit/return). NULL
       for a window the fetcher could not reconcile or a file fetched before
       the count was read; the page then shows no return-visit figure. byApp is
       the return visits by app, the ten most. */
    visits: %s
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

  /* The shorter windows the timeframe buttons offer, keyed by day count, each
     with every variable above for its own period. The lists were read off the
     dashboard for that period; the daily series and the per-day referrer rows
     are the full window's cut to length. Empty when the data file predates
     the per-window fetch, and the page then shows no buttons. */
  var WINDOWS = %s;
%s''' % (
        BEGIN, start, end, daily,
        json.dumps(engine(gsc, start, end), separators=(",", ":")),
        json.dumps(engine(bing, start, end), separators=(",", ":")),
        ",\n    ".join(json.dumps(r, separators=(", ", ": ")) for r in day_refs(gc)),
        rows(bd["instances"]), rows(bd["layers"]), rows(bd["refs"]),
        rows(bd["systems"]), rows(bd["browsers"]), rows(bd["actions"]),
        rows(bd["geo"]), rows(bd["campaigns"], 2),
        rows(bd["mapLinkSources"], 2), rows(bd["mapLinkResults"], 2),
        rows(bd["mapLinkPlaces"], 2),
        json.dumps(bd["mapLinks"], separators=(", ", ": "), sort_keys=True),
        "null" if bd["geoSuccess"] is None else str(bd["geoSuccess"]),
        compact(bd["layerScope"]), compact(bd["layerSplit"]),
        compact(bd["layerPooled"]), bd["layerSplitFrom"],
        bd["seo"]["police"], bd["seo"]["school"],
        residual,
        "true" if bd["pagesCut"] else "false",
        json.dumps(bd["notListedYet"], separators=(",", ":")),
        compact(bd["listedPartway"]),
        compact(bd["visits"]),
        "{:,}".format(gc["total"]), "{:,}".format(daily_sum),
        "{:,}".format(abs(gc["total"] - daily_sum)),
        datetime.date.fromisoformat(gc["fetched"][:10]).strftime("%B %-d, %Y"),
        int(start[:4]), gc["total"],
        compact(wins).replace("</", "<\\/"), END)

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
    print("  %-16s %d (in no bar)" % ("(no app)", residual))
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
