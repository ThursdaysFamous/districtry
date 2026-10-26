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
import math
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# The day the layer event started carrying the instance tag (engine
# overlay-cards). Before it, `layer/<id>` pooled every app registering that id;
# after it, `layer/<tag>/<id>`. A historical fact that never moves, and the
# page needs it to date its own partial attribution.
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
                  "mo": "Missouri",
                  "landing": "Front page"}
# The day each instance was first LISTED on the front door, measured once with
#   git log --reverse --format=%cs -S'"tag": "<tag>"' -- metros.json
# and recorded here rather than re-read, so this build needs no git and cannot
# be wrong in a shallow clone (the sitemap lesson). These are historical facts
# that never move, like LAYER_SPLIT above. Used for ONE comparison:
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
                "ms": "2026-10-16", "la": "2026-10-21",
                "mo": "2026-10-26"}
# GoatCounter publishes a referrer's HOST; these are the names a reader knows.
# A host with no entry ships exactly as GoatCounter spells it.
REF_NAMES = {"(unknown)": "Direct / unknown", "duckduckgo.com": "DuckDuckGo",
             "noai.duckduckgo.com": "DuckDuckGo",
             "safe.duckduckgo.com": "DuckDuckGo",
             "go.bsky.app": "Bluesky", "www.bing.com": "Bing",
             "bing.com": "Bing", "cn.bing.com": "Bing",
             "bsky.app": "Bluesky", "www.google.com": "Google",
             "search.brave.com": "Brave", "www.reddit.com": "Reddit",
             "www.ecosia.org": "Ecosia", "www.startpage.com": "Startpage",
             "chatgpt.com": "ChatGPT", "copilot.com": "Copilot",
             "www.facebook.com": "Facebook", "facebook.com": "Facebook",
             "l.instagram.com": "Instagram", "www.linkedin.com": "LinkedIn",
             "com.linkedin.android": "LinkedIn",
             # The share popover tags a copied link ?ref=share and a QR code
             # ?ref=qr (engine permalink), and GoatCounter takes ref= as the
             # source.
             "share": "Shared links", "qr": "QR codes",
             # The Play app opens its start page as /app/?ref=play, and a
             # link opened straight into it carries the app as its referrer.
             "play": "Android app", "com.districtry.app": "Android app"}
# Search engines, by the display name above, for the "search engines sent"
# sentence.
SEARCH_ENGINES = {"Google", "DuckDuckGo", "Bing", "Yahoo", "Ecosia",
                  "Startpage", "Brave"}
# The per-day source chart's groups. A referrer key in none of these, other
# than "(unknown)" and the Android app, counts as "Other sites".
DAY_REF_GROUPS = [
    ("Google", {"Google", "www.google.com", "google.com"}),
    ("DuckDuckGo", {"duckduckgo.com", "noai.duckduckgo.com",
                    "safe.duckduckgo.com", "DuckDuckGo"}),
    ("Bing", {"www.bing.com", "bing.com", "cn.bing.com", "Bing"}),
    ("Other search engines", {"Yahoo", "search.yahoo.com", "yahoo.com",
                              "www.ecosia.org", "ecosia.org",
                              "www.startpage.com", "startpage.com",
                              "search.brave.com", "kagi.com", "www.qwant.com",
                              "yandex.ru", "yandex.com", "www.baidu.com"}),
]
NO_SOURCE = "(unknown)"
# The Google Play app's two sources, counted apart because during the closed
# test its testers are a different population from the site's readers.
ANDROID_APP = {"play", "com.districtry.app"}

# WHAT EACH EVENT FAMILY IS, which is the whole difference between counting use
# and counting the counter. GoatCounter files everything that is not a page
# view as an event, and three different things send one:
#
#   * a READER doing something — choosing a point, turning on a layer;
#   * a RESULT of something a reader did, counted a second time — the location
#     that was found, the hand-off to another state's map;
#   * the app counting ITSELF with nobody doing anything — the visit counter
#     every map sends on opening (since 2026-10-22), an install prompt shown.
#
# Measured on 2026-10-26's file, the third kind was 22% of all events in the
# last seven days and none before 2026-10-13, so a chart of "events" rose for a
# week while what readers did stayed level. Each family is named in exactly one
# table. A family in none is counted as a reader action AND PRINTED, because a
# new counter is far likelier to be a new feature than a new automatic count,
# and a build that failed on it would stop the daily refresh.
#
# The groups are the bars of "What readers do", in order; the label must fit
# the bar column's 112px.
ACTION_GROUPS = [
    ("Points chosen", {"select"}),
    ("Layers turned on", {"layer"}),
    ("Searches", {"address-search", "district-search"}),
    ("Location requests", {"geolocate"}),
    ("ZIP searches", {"zip-search"}),
    ("Street names", {"boundary-streets"}),
    ("Comparisons", {"compare", "compare-stop", "compare-stats",
                     "compare-stats-row", "compare-stats-reopen",
                     "compare-stats-print", "compare-stats-link"}),
    ("Install prompts", {"install-invite/closed", "install-invite/tip-closed",
                         "install-invite/test-closed",
                         "install-invite/test-join", "app-install"}),
    ("Sharing", {"share-open", "share-qr", "share-native", "share-permalink",
                 "copy-coordinates", "share-in"}),
    ("Data gaps", {"gaps-open", "gaps-why", "gaps-suggest"}),
    ("Feedback", {"feedback-open", "feedback-send", "feedback-link"}),
    ("Other", {"more-open", "more-item", "osm-note", "example-place",
               "app-shortcut"}),
]
# The daily chart's four bands of reader actions, by ACTION_GROUPS label.
DAY_ACTION_BANDS = [("points", {"Points chosen"}),
                    ("layers", {"Layers turned on"}),
                    ("searches", {"Searches", "Location requests",
                                  "ZIP searches"})]
RESULT_FAMILIES = {"geolocate-success", "locate-fail", "metro-portal-go",
                   "map-link-read", "map-link"}
AUTOMATIC_FAMILIES = {"visit/first", "visit/return", "app-launch",
                      "install-invite/shown", "install-invite/tip-shown",
                      "install-invite/test-shown"}
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
    """One row per fetched day: [label, google, ddg, bing, other engines,
    other sites, android app, direct, within the site, cut-short].

    PAGE VISITS ONLY. The per-day list counted every hit until 2026-10-26, so
    a source's figure carried the layers and points its visitors went on to
    use: "facebook.com 17" that day was two page visits and fifteen actions
    from the same two browsers. A source's page visits are its ARRIVALS, and
    Google's agree with what Search Console reports as clicks (340 against 326
    over 19-24 October, measured 2026-10-26), which the all-hit figure, about
    1.7 times as large, did not.

    "Within the site" is the day's page visits that no source row carries:
    about a third of them. That they are pages reached from a link on
    districtry itself is INFERRED, not read: the counter lists no districtry
    row at all, and the agreement with Search Console says a Google arrival is
    counted once and not again on the pages it led to.

    A file fetched before the per-day lists existed has no `daily_referrers`,
    and one fetched before 2026-10-26 no `page_rows`; the page then hides the
    section rather than drawing a chart of zeroes, which would read as "nobody
    arrived". A day whose list was cut short keeps its flag, because the rows
    it did not send are the smallest and would have been "Other sites".
    """
    out = []
    pv = {d["date"]: d["pageviews"] for d in gc["daily"]}
    for d in gc.get("daily_referrers", []):
        if "page_rows" not in d:
            return []
        counts = {name: 0 for name, _ in DAY_REF_GROUPS}
        other = none = app = 0
        for r in d["page_rows"]:
            for name, keys in DAY_REF_GROUPS:
                if r["key"] in keys or r["label"] in keys:
                    counts[name] += r["count"]
                    break
            else:
                if r["key"] == NO_SOURCE:
                    none += r["count"]
                elif r["key"] in ANDROID_APP:
                    app += r["count"]
                else:
                    other += r["count"]
        listed = sum(r["count"] for r in d["page_rows"])
        within = pv.get(d["date"], 0) - listed
        if within < 0:
            # More arrivals than page visits would mean the inference above is
            # wrong, so it is printed rather than drawn as a negative band.
            print("WARN %s: %d page visits carry a source, more than the %d "
                  "page visits that day" % (d["date"], listed,
                                            pv.get(d["date"], 0)))
            within = 0
        out.append([label(d["date"])] + [counts[n] for n, _ in DAY_REF_GROUPS]
                   + [other, app, none, within, bool(d.get("page_more"))])
    return out


def families(gc):
    """The event families as the page reads them, one series per kind.

    Returns ({group label: daily[]}, automatic daily[], results daily[],
    unclassified {family: count}). FAILS on a file without the per-family
    series, and on one whose families do not add up to the daily events, day
    by day: the split below is only worth publishing if it is a split of the
    same events the chart used to draw.
    """
    ef = gc.get("event_families")
    if ef is None:
        fail("data/goatcounter-traffic.json carries no event_families. It was "
             "fetched before 2026-10-26; run the fetch workflow again.")
    n = len(gc["daily"])
    for i, d in enumerate(gc["daily"]):
        got = sum(f["daily"][i] for f in ef.values())
        if got != d["events"]:
            fail("events on %s: the families add up to %d against %d in the "
                 "daily series%s" % (d["date"], got, d["events"],
                                     " (the events list was cut short)"
                                     if gc.get("events_cut") else ""))
    owner = {}
    for name, fams in ACTION_GROUPS:
        for f in fams:
            owner[f] = name
    groups = {name: [0] * n for name, _ in ACTION_GROUPS}
    auto, results, unknown = [0] * n, [0] * n, {}
    for fam, f in ef.items():
        if fam in AUTOMATIC_FAMILIES:
            into = auto
        elif fam in RESULT_FAMILIES:
            into = results
        else:
            if fam not in owner:
                unknown[fam] = f["count"]
            into = groups[owner.get(fam, "Other")]
        for i, v in enumerate(f["daily"]):
            into[i] += v
    return groups, auto, results, unknown


def page_kind_series(gc):
    """Page visits per day to a state's map, the front page and the rest,
    held to the daily page visits day by day."""
    pk = gc.get("page_kinds")
    if pk is None:
        fail("data/goatcounter-traffic.json carries no page_kinds. It was "
             "fetched before 2026-10-26; run the fetch workflow again.")
    for i, d in enumerate(gc["daily"]):
        got = pk["app"][i] + pk["front"][i] + pk["other"][i]
        if got != d["pageviews"]:
            fail("page visits on %s: the map, front page and other pages add "
                 "up to %d against %d" % (d["date"], got, d["pageviews"]))
    return pk


def daily_rows(gc):
    """[label, maps, front page, other pages, points, layers, searches and
    location, other reader actions, automatic, results] per day."""
    pk = page_kind_series(gc)
    groups, auto, results, _ = families(gc)
    band_of = {}
    for band, names in DAY_ACTION_BANDS:
        for nm in names:
            band_of[nm] = band
    out = []
    for i, d in enumerate(gc["daily"]):
        b = {"points": 0, "layers": 0, "searches": 0, "other": 0}
        for name, series in groups.items():
            b[band_of.get(name, "other")] += series[i]
        out.append([label(d["date"]), pk["app"][i], pk["front"][i],
                    pk["other"][i], b["points"], b["layers"], b["searches"],
                    b["other"], auto[i], results[i]])
    return out


def slice_of(gc, name):
    """One of the fetcher's slices, or a FAIL naming the fetch to rerun."""
    sl = gc.get("slices", {}).get(name)
    if sl is None:
        fail("the data file carries no %r slice. It was fetched before "
             "2026-10-26; run the fetch workflow again." % name)
    return sl


def merged(rows_, table):
    """Rows renamed through `table` and summed where two keys share a name
    (www.bing.com and bing.com are both Bing), largest first."""
    out = {}
    for r in rows_:
        nm = table.get(r["key"], r["label"] or r["key"])
        out[nm] = out.get(nm, 0) + r["count"]
    return sorted(out.items(), key=lambda kv: (-kv[1], kv[0]))


def people(gc, days):
    """Visitors for one window, out of the page-visit and launch slices.

    `days` is this window's slice of daily_rows(), so the page kinds and the
    action counts cover exactly the days the slices were read for.
    """
    pv = slice_of(gc, "pageview")
    launch = slice_of(gc, "launch")
    us = lambda sl: sum(r["count"] for r in sl["locations"] if r["key"] == "US")
    # THE COUNTRY SHARE IS TAKEN OF WHAT THE BREAKDOWNS COUNT, NOT OF THE
    # TOTAL. Every breakdown of a slice (screens, browsers, systems, countries)
    # adds up to the same figure, a little under the slice's own total — 5,466
    # against 5,512 page visits on 2026-10-26's file — and the difference has
    # no country. Taking "outside the United States" as the total less the
    # United States would have counted those 46 as foreign. The screen list is
    # complete where the country list stops at its top entries, so its sum is
    # the denominator.
    charted = lambda sl: sum(r["count"] for r in sl["sizes"])
    arrivals = sum(r["count"] for r in pv["referrers"])
    refs = merged(pv["referrers"], REF_NAMES)
    search = sum(n for nm, n in refs if nm in SEARCH_ENGINES)
    android = sum(r["count"] for r in pv["referrers"] if r["key"] in ANDROID_APP)
    direct = sum(r["count"] for r in pv["referrers"] if r["key"] == NO_SOURCE)
    col = lambda i: sum(d[i] for d in days)
    return {
        "visits": arrivals,
        "visitsCut": bool(pv["referrers_cut"]),
        "search": search,
        "android": android,
        "direct": direct,
        # Other websites, shared links and QR codes: every source left.
        "sites": arrivals - search - android - direct,
        "pages": pv["count"],
        "charted": charted(pv),
        "maps": col(1), "front": col(2), "other": col(3),
        "us": us(pv),
        "abroad": charted(pv) - us(pv),
        "launches": launch["count"],
        "launchesAbroad": charted(launch) - us(launch),
    }


def use(gc, days, start):
    """What readers did in one window: the action groups summed over its
    days, the automatic counts and the results, and each per map opening."""
    groups, auto, results, _ = families(gc)
    first = len(gc["daily"]) - len(days)
    acts = [(name, sum(groups[name][first:])) for name, _ in ACTION_GROUPS]
    return {
        "actions": acts,
        "total": sum(n for _, n in acts),
        "automatic": sum(auto[first:]),
        "results": sum(results[first:]),
    }


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


def bar_data(gc, start, end, full, days):
    """barData for one window, as the page reads it, plus the instance rows
    and their residual for the reconciliation printout.

    `gc` is the whole fetched file for the full window, or one of its
    `windows` entries for a shorter one: both carry the same lists, read off
    the dashboard for their own period. `full` is always the whole file, whose
    per-day series are cut to this window's `days` (daily_rows() rows).

    THE SOURCES, SCREENS, SYSTEMS, BROWSERS AND COUNTRIES ARE PAGE VISITS
    ONLY since 2026-10-26. They were read off the dashboard's unfiltered
    widgets, which count every hit, so a source or a country weighed what its
    visitors went on to do as well as how many came: "search engines sent
    4,355 visits" was 2,519 page visits that day, the rest the layers and
    points those visits used. A share of readers is a share of page visits.
    """
    instances, residual = split_by_instance(gc, gc["pageviews"])
    pg = {r["path"]: r["count"] for r in gc["pages"]}
    pv = slice_of(gc, "pageview")
    ef = full["event_families"]
    first = len(full["daily"]) - len(days)
    fam = lambda name: sum(ef[name]["daily"][first:]) if name in ef else 0
    u = use(full, days, start)
    acts = sorted((r for r in u["actions"] if r[1] and r[0] != "Other"),
                  key=lambda r: -r[1])
    acts += [r for r in u["actions"] if r[0] == "Other" and r[1]]
    size = {r["key"]: r["count"] for r in pv["sizes"]}
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
        "refs": merged(pv["referrers"], REF_NAMES)[:8],
        "systems": pairs(pv["systems"]),
        "browsers": pairs(pv["browsers"]),
        "sizes": [("Phones", size.get("phone", 0)),
                  ("Tablets", size.get("tablet", 0)),
                  ("Computers", size.get("desktop", 0) + size.get("desktophd", 0))],
        "actions": acts,
        "geo": pairs(pv["locations"][:8]),
        "people": people(gc, days),
        "use": {"total": u["total"], "automatic": u["automatic"],
                "results": u["results"]},
        "campaigns": pairs(gc["campaigns"]),
        "mapLinkSources": ml_sources,
        "mapLinkResults": ml_results,
        "mapLinkPlaces": ml_places,
        "mapLinks": ml,
        # Read from the family series, which hold every event path, so the
        # success count can no longer fall off a ten-row list (the 2026-09-23
        # "0 of 88"). Still null when the file has no such family at all.
        "geoTries": fam("geolocate"),
        "geoSuccess": fam("geolocate-success") if "geolocate-success" in ef
                      else None,
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
        rows_ = daily_rows(gc)[-n:]
        bd = bar_data(w, start, end, gc, rows_)[0]
        out[key] = {
            "daily": rows_,
            "searchData": engine(gsc, start, end, key),
            "bingData": engine(bing, start, end, key),
            "dayRefs": [r for r in day_refs(gc)[-n:]],
            "barData": bd,
            "META": {"total": w["total"], "year": int(start[:4])},
        }
    return out


def jsround(x):
    """Math.round, which the page's script uses: Python's round() takes a
    half to the even neighbour, so 44.5 would be 44 here and 45 on the page."""
    return int(math.floor(x + 0.5))


def jspct(a, b):
    # a / b * 100 in that order, as the page writes it: 100 * a / b can land
    # on the other side of a half.
    return "%d%%" % jsround(a / b * 100) if b else "—"


def build():
    gc = load("goatcounter-traffic.json")
    gsc = load("search-performance.json")
    bing = load("bing-search-performance.json")
    start, end = gc["window"]["start"], gc["window"]["end"]

    check_instance_names()
    days = daily_rows(gc)
    daily = ",\n    ".join(json.dumps(r, separators=(", ", ": ")) for r in days)
    bd, instances, residual = bar_data(gc, start, end, gc, days)
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

  /* One row a day: [day, pages viewed on a state's map, on the front page, on
     any other page, then what readers did: points chosen, layers turned on,
     searches and location requests, other actions, then the two kinds of
     event that are NOT a reader doing something: automatic counts and
     results]. The first three add up to the day's page visits and the last
     six to its events, which the builder checks day by day. */
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

  /* Where each of the last days' visits came from, each day asked for on its
     own and for page visits alone: [day, Google, DuckDuckGo, Bing, other
     search engines, other sites, the Android app, no source, page visits no
     source row carries (reached from within the site, inferred), list cut
     short]. Empty when the data file predates the per-day page-visit fetch. */
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
    /* Sources, screens, systems, browsers and countries are PAGE VISITS
       ONLY. They used to count every hit, so a source weighed what its
       visitors went on to do as well as how many came. */
    refs: [
      %s
    ],
    sizes: [
      %s
    ],
    systems: [
      %s
    ],
    browsers: [
      %s
    ],
    /* What readers did, by kind, out of every event path the dashboard holds:
       never the automatic counts or the results. See ACTION_GROUPS. */
    actions: [
      %s
    ],
    geo: [
      %s
    ],
    campaigns: [
      %s
    ],
    /* Visitors for this window. `visits` is page visits that came with a
       source, the closest this counter gets to a count of visits; `android`
       is those from the Google Play app and `direct` those with no source;
       `pages` is all page visits and `maps`, `front` and `other` split them;
       `abroad` is page visits from outside the United States; `launches` is
       the installed app opened, and `launchesAbroad` those outside the United
       States. */
    people: %s,
    /* Reader actions in all, and the two kinds of event left out of them. */
    use: %s,
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
    /* Location requests and how many found the reader. geoSuccess is NULL,
       NOT ZERO, when the file holds no such event at all: absence and zero
       are different facts, and on 2026-09-23 the row fell off a ten-row list
       and the page published "succeeds 0%% of the time: 0 of 88". Both now
       come from the per-family series, which hold every event path. */
    geoTries: %d,
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
       total      — GoatCounter's own js-total-utc for the window, page visits
                    and events together. The daily columns sum to %s — %s
                    apart, and the SIGN FLIPS day to day (61 the other way on
                    2026-09-14), which rules out a fixed offset. Both count the
                    same period and this page does not know what the
                    difference is, so both are printed and neither is derived
                    from the other.

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
        rows(bd["sizes"]), rows(bd["systems"]), rows(bd["browsers"]),
        rows(bd["actions"]), rows(bd["geo"]), rows(bd["campaigns"], 2),
        compact(bd["people"]), compact(bd["use"]),
        rows(bd["mapLinkSources"], 2), rows(bd["mapLinkResults"], 2),
        rows(bd["mapLinkPlaces"], 2),
        json.dumps(bd["mapLinks"], separators=(", ", ": "), sort_keys=True),
        bd["geoTries"],
        "null" if bd["geoSuccess"] is None else str(bd["geoSuccess"]),
        compact(bd["layerScope"]), compact(bd["layerSplit"]),
        compact(bd["layerPooled"]), bd["layerSplitFrom"],
        bd["seo"]["police"], bd["seo"]["school"],
        residual,
        "true" if bd["pagesCut"] else "false",
        json.dumps(bd["notListedYet"], separators=(",", ":")),
        compact(bd["listedPartway"]),
        compact(bd["visits"]),
        "{:,}".format(daily_sum),
        "{:,}".format(abs(gc["total"] - daily_sum)),
        datetime.date.fromisoformat(gc["fetched"][:10]).strftime("%B %-d, %Y"),
        int(start[:4]), gc["total"],
        compact(wins).replace("</", "<\\/"), END)

    # The fallbacks a crawler reads, for the full window. Each is computed the
    # way the page's script computes it, so the text does not change on load;
    # everything else keeps its literal and is printed below.
    n = len(days)
    fmt = "{:,}".format
    ppl, u = bd["people"], bd["use"]
    act = dict(bd["actions"])
    maps = ppl["maps"]
    points = act.get("Points chosen", 0)
    layers_on = act.get("Layers turned on", 0)
    searches = act.get("Searches", 0) + act.get("ZIP searches", 0)
    per_map = lambda v: ("%.1f" % (v / maps)) if maps else "—"
    pages_of = lambda d: d[1] + d[2] + d[3]
    acts_of = lambda d: d[4] + d[5] + d[6] + d[7]
    listing = lambda vals: "".join(
        ("" if i == 0 else " and " if i == len(vals) - 1 else ", ") + fmt(v)
        for i, v in enumerate(vals))
    weekday = lambda i: datetime.date.fromisoformat(
        gc["daily"][i]["date"]).strftime("%A")
    fallbacks = {
        # LONG month names, matching the page's own longMonth(): a literal in a
        # different format from what the script writes makes the text visibly
        # change on load, which is its own small lie about the measurement.
        "range": "%s – %s, %d" % (long_label(start), long_label(end), int(end[:4])),
        "days": str(n),
        "total": fmt(gc["total"]),
        "pageviews": fmt(gc["pageviews"]),
        "perDay": str(jsround(gc["pageviews"] / n)),
        "dailySum": fmt(daily_sum),
        "dailyGap": fmt(abs(gc["total"] - daily_sum)),
        "exportDate": datetime.date.fromisoformat(
            gc["fetched"][:10]).strftime("%B %-d, %Y"),
        "visits": fmt(ppl["visits"]),
        "visitsPerDay": str(jsround(ppl["visits"] / n)),
        "searchVisits": fmt(ppl["search"]),
        "siteVisits": fmt(ppl["sites"]),
        "androidVisits": fmt(ppl["android"]),
        "directVisits": fmt(ppl["direct"]),
        "visitsLeft": fmt(max(0, ppl["pages"] - ppl["visits"])),
        "mapOpenings": fmt(maps),
        "frontPages": fmt(ppl["front"]),
        "otherPages": fmt(ppl["other"]),
        "chartedPages": fmt(ppl["charted"]),
        "usCount": fmt(ppl["us"]),
        "usPct": jspct(ppl["us"], ppl["charted"]),
        "abroadPages": fmt(ppl["abroad"]),
        "abroadPct": jspct(ppl["abroad"], ppl["charted"]),
        "launches": fmt(ppl["launches"]),
        "launchesAbroad": fmt(ppl["launchesAbroad"]),
        "readerActions": fmt(u["total"]),
        "actionsPerMap": per_map(u["total"]),
        "pointsChosen": fmt(points),
        "pointShare": jspct(points, maps),
        "layersOn": fmt(layers_on),
        "layersPerMap": per_map(layers_on),
        "searchesAll": fmt(searches),
        "geoAttempts": fmt(bd["geoTries"]),
        "otherActions": fmt(u["total"] - points - layers_on - searches
                            - bd["geoTries"]),
        "autoCount": fmt(u["automatic"]),
        "resultCount": fmt(u["results"]),
        "refNote": ref_note(bd),
        "lastDay": long_label(gc["daily"][-1]["date"]),
        "recentDays": listing([pages_of(d) for d in days[-4:]]),
        "recentActions": listing([acts_of(d) for d in days[-4:]]),
    }
    # The peak day, computed the way the page computes it: the day with the
    # most pages viewed, the first of a tie. It used to be pages and events
    # together, and since 2026-10-22 every map opening also sends a visit
    # count, so that figure rose by about a third with no change in readers.
    peak_i = max(range(n), key=lambda i: (pages_of(days[i]), -i))
    top = pages_of(days[peak_i])
    fallbacks["peak"] = fmt(top)
    fallbacks["peakLabel"] = "%s, %s" % (weekday(peak_i), days[peak_i][0])
    tied = ["%s, %s" % (weekday(i), days[i][0]) for i in range(n)
            if i != peak_i and pages_of(days[i]) == top]
    fallbacks["peakTieNote"] = ", tied with " + " and ".join(tied) if tied else ""
    size = dict(bd["sizes"])
    fallbacks["mobilePct"] = jspct(size["Phones"] + size["Tablets"],
                                   sum(size.values()))
    fallbacks["topTwoBrowserPct"] = jspct(
        sum(c for _, c in bd["browsers"][:2]), sum(c for _, c in bd["browsers"]))
    fallbacks["barSumNote"] = bar_sum_note(bd)
    fallbacks["useTrend"] = use_trend(days)
    fallbacks["playNote"] = play_note(ppl, wins, n, "these two months")
    return block, gc, instances, residual, daily_sum, fallbacks


WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven",
         "eight", "nine", "ten", "eleven", "twelve"]


def bar_sum_note(bd):
    """The page's barSumNote for the full window, word for word."""
    fmt = "{:,}".format
    total = lambda key: sum(c for _, c in bd[key])
    sums = [total("sizes"), total("browsers"), total("systems")]
    pages = bd["people"]["pages"]
    if sums[0] == sums[1] == sums[2]:
        gap = pages - sums[0]
        head = ("The screen, browser and system charts each add up to "
                + ("the pages viewed" if gap == 0 else
                   "%s, %s %s than the pages viewed"
                   % (fmt(sums[0]), fmt(abs(gap)),
                      "fewer" if gap > 0 else "more")))
    else:
        head = ("The screen chart adds up to %s, the browser chart to %s and "
                "the system chart to %s, against %s pages viewed"
                % (fmt(sums[0]), fmt(sums[1]), fmt(sums[2]), fmt(pages)))
    geo = total("geo")
    if geo == bd["people"]["charted"]:
        return head + ", and the country chart adds up to %s." % fmt(geo)
    n = len(bd["geo"])
    return head + (", and the country chart shows only the %s with the most."
                   % (WORDS[n] if n < len(WORDS) else n))


def ref_note(bd):
    """The page's refNote for the full window, word for word."""
    fmt = "{:,}".format
    shown, visits = sum(c for _, c in bd["refs"]), bd["people"]["visits"]
    if shown == visits:
        return "The sources chart shows every source."
    n = len(bd["refs"])
    return ("The sources chart shows the %s largest, %s of the %s visits."
            % (WORDS[n] if n < len(WORDS) else n, fmt(shown), fmt(visits)))


def use_trend(days):
    """The page's useTrend: reader actions per map opened and the share of
    map openings with a point chosen, the last seven days against the seven
    before, from the full window's day rows."""
    if len(days) < 14:
        return ""

    def rate(rows_):
        maps = sum(d[1] for d in rows_)
        acts = sum(d[4] + d[5] + d[6] + d[7] for d in rows_)
        pts = sum(d[4] for d in rows_)
        return ("%.1f" % (acts / maps) if maps else "—"), jspct(pts, maps)

    now, before = rate(days[-7:]), rate(days[-14:-7])
    return ("In the last seven days readers took %s actions for each map "
            "opened and chose a point in about %s of them, against %s and %s "
            "in the seven days before." % (now + before))


def play_note(ppl, wins, n, period):
    """The page's playNote for one window, word for word."""
    fmt = "{:,}".format
    x, y = ppl["launches"], ppl["launchesAbroad"]
    if not x:
        return "The installed app was not opened in %s." % period
    line = ("The installed app was opened %s %s in %s, %s of them outside "
            "the United States." % (fmt(x), "time" if x == 1 else "times",
                                    period, fmt(y)))
    w7 = wins.get("7")
    if y * 2 > x and w7 and n > 7:
        abroad7 = w7["barData"]["people"]["abroad"]
        now = jsround(abroad7 / 7)
        before = jsround((ppl["abroad"] - abroad7) / (n - 7))
        if now > before:
            return (line + " Before the last seven days the site barely "
                    "reached readers abroad: pages viewed from outside the "
                    "United States averaged %s a day, against %s a day in the "
                    "last seven days. So these launches are more likely people "
                    "trying the app than readers looking up their own "
                    "districts." % (fmt(before), fmt(now)))
    return line


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
    f = fallbacks
    print("visitors: %s page visits came with a source (%s from the Android "
          "app, %s with none); %s pages viewed, %s of them on a map; %s from "
          "outside the US"
          % (f["visits"], f["androidVisits"], f["directVisits"], f["pageviews"],
             f["mapOpenings"], f["abroadPct"]))
    print("use: %s reader actions (%s per map opening), %s points chosen "
          "(%s of map openings), %s layers turned on; not counted as use: "
          "%s automatic counts, %s results"
          % (f["readerActions"], f["actionsPerMap"], f["pointsChosen"],
             f["pointShare"], f["layersOn"], f["autoCount"], f["resultCount"]))
    unknown = families(gc)[3]
    if unknown:
        # Counted as reader actions under "Other". Name it in ACTION_GROUPS,
        # RESULT_FAMILIES or AUTOMATIC_FAMILIES, whichever it is.
        print("UNCLASSIFIED event families, counted as reader actions: %s"
              % ", ".join("%s (%d)" % kv for kv in sorted(unknown.items())))
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
