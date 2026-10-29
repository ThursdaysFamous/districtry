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
    The one exception is the Milestones tab (added 2026-10-27), which this
    writes whole between its TRAFFIC-MILESTONES markers, sentences and all,
    because every sentence there is built from a figure. The day each mark was
    first passed is kept in data/traffic-milestones.json, which this also
    writes, and a mark newly passed is printed as a MILESTONE line.
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
from html import escape as escape_html
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
    # Sponsor became a button beside Feedback on 2026-10-29 (Adam: "the
    # sponsor button needs to be more visible"); sponsor/<tag>, and
    # sponsor/front on the front page
    ("Sponsor", {"sponsor"}),
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
# THE FIRST-VISIT HELP IS A FOURTH KIND, counted apart from all three (engine
# first-use, 2026-10-28). Adam, that day: "I want to make sure that the
# tutorial is properly tracked and excluded from the main traffic stats. i do
# want to trac kusage though". A press on the tip or its tour is a reader doing
# something, but to the help rather than to the map, and as a reader action it
# would have raised that figure the day the help shipped with no change in how
# the map was used. Each step is its own family (TWO_PART_FAMILIES in
# goatcounter_fetch.py) and, from the day each count began naming its map,
# kept map by map ("The tutorial stats should track app used on"). The front
# page's own tip (PR #1795) sends the same steps with `front` where a map puts
# its tag (`first-use/got-it/front`, the map-link-read/front convention), and
# is its own row. Any
# family under the prefix counts as the help's; one that is not a step here is
# in the total and in no column, and is PRINTED. The How to use page is an
# ordinary page and stays in the pages viewed ("keep"); its views are shown
# beside the presses as well.
TUTORIAL_PREFIX = "first-use"
TUTORIAL_FROM = "2026-10-28"
TUTORIAL_STEPS = [("got-it", "Got it"),
                  ("tour", "Took the tour"),
                  ("tour-done", "Finished it"),
                  ("tour-closed", "Left partway"),
                  ("help", "Opened How to use")]
TUTORIAL_FRONT_TAG = "front"
# The front page counts visit/first/front and visit/return/front, "front"
# where a map puts its tag (build_landing_page.py visit_count_script), since
# VISIT_FRONT_FROM. A visit is counted once, on the page it starts on.
VISIT_FRONT_TAG = "front"
VISIT_FRONT_NAME = "the front page"
VISIT_FRONT_FROM = "2026-10-29"


def tutorial_family(step):
    return "%s/%s" % (TUTORIAL_PREFIX, step)
TUTORIAL_BEGIN = "<!-- ==== TRAFFIC-TUTORIAL:BEGIN ==== -->"
TUTORIAL_END = "<!-- ==== TRAFFIC-TUTORIAL:END ==== -->"


def is_tutorial(fam):
    return fam == TUTORIAL_PREFIX or fam.startswith(TUTORIAL_PREFIX + "/")


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


def map_link_summary(gc, start):
    """The map-link rows as the page draws them: three bar groups and a
    summary the lead sentence reads. Fails on a row whose path is not the
    event's six parts, because a row this cannot read would otherwise drop out
    of every total without a word.

    `fromInside` says whether the count began inside the window starting at
    `start`. A shorter window that starts after it was counted in full, so
    its sentence says "in these 7 days" rather than "since October 17": the
    7-day view used to say no link had been read since October 17 when two
    had been, on days before the window began."""
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
        "fromInside": MAP_LINKS_FROM >= start,
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
    first-visit help daily[], unclassified {family: count}). FAILS on a file
    without the per-family
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
    auto, results, tutorial, unknown = [0] * n, [0] * n, [0] * n, {}
    steps = {tutorial_family(f) for f, _ in TUTORIAL_STEPS}
    for fam, f in ef.items():
        if fam in AUTOMATIC_FAMILIES:
            into = auto
        elif fam in RESULT_FAMILIES:
            into = results
        elif is_tutorial(fam):
            if fam not in steps:
                unknown[fam] = f["count"]
            into = tutorial
        else:
            if fam not in owner:
                unknown[fam] = f["count"]
            into = groups[owner.get(fam, "Other")]
        for i, v in enumerate(f["daily"]):
            into[i] += v
    return groups, auto, results, tutorial, unknown


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
    location, other reader actions, automatic, results, first-visit help,
    first visits, return visits] per day.

    The last two are None on a day before the visit count began (`visits`
    `since`) and on every day when the file carries no visit counts, so a day
    nobody counted reads as not counted, never as 0. They are counted with the
    automatic counts as well (AUTOMATIC_FAMILIES); these two columns split the
    visit counter's part of them for the first and return visits chart."""
    pk = page_kind_series(gc)
    groups, auto, results, tutorial, _ = families(gc)
    v = gc.get("visits")
    if v and not (len(v["first_daily"]) == len(v["return_daily"]) == len(gc["daily"])):
        fail("visits: %d first and %d return days against %d in the daily "
             "series" % (len(v["first_daily"]), len(v["return_daily"]),
                         len(gc["daily"])))
    band_of = {}
    for band, names in DAY_ACTION_BANDS:
        for nm in names:
            band_of[nm] = band
    out = []
    for i, d in enumerate(gc["daily"]):
        b = {"points": 0, "layers": 0, "searches": 0, "other": 0}
        for name, series in groups.items():
            b[band_of.get(name, "other")] += series[i]
        counted = bool(v) and d["date"] >= v["since"]
        out.append([label(d["date"]), pk["app"][i], pk["front"][i],
                    pk["other"][i], b["points"], b["layers"], b["searches"],
                    b["other"], auto[i], results[i], tutorial[i],
                    v["first_daily"][i] if counted else None,
                    v["return_daily"][i] if counted else None])
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
    days, the automatic counts, the results and the first-visit help."""
    groups, auto, results, tutorial, _ = families(gc)
    first = len(gc["daily"]) - len(days)
    acts = [(name, sum(groups[name][first:])) for name, _ in ACTION_GROUPS]
    return {
        "actions": acts,
        "total": sum(n for _, n in acts),
        "automatic": sum(auto[first:]),
        "results": sum(results[first:]),
        "tutorial": sum(tutorial[first:]),
    }


def tutorial_use(full, days, end):
    """The first-visit help for one window: each step's presses, each map's
    row of them, the front page's, the presses no map is named for, and the
    How to use page's views. `full` is the whole file, whose per-day series
    are cut to this window's `days`, as use() cuts them.

    A press is named for its map from the day the counts began carrying the
    map's tag; the presses before that day are in each step's total and in no
    map's row, and the `unnamed` row says how many. `totals` is every press,
    the front page's included. `front` is None until the front page's tip has
    been pressed. `play` is the presses made inside the Google Play app,
    which are in the rows above it as well, or None for a file fetched before
    they were kept apart. `helpPage` is None for a file fetched before the
    page's own series was kept.
    """
    ef = full["event_families"]
    first = len(full["daily"]) - len(days)
    cut = lambda series: sum(series[first:])
    totals = [cut(ef[tutorial_family(f)]["daily"]) if tutorial_family(f) in ef else 0
              for f, _ in TUTORIAL_STEPS]
    by_app = full.get("event_by_app", {})
    maps = {}
    for j, (f, _) in enumerate(TUTORIAL_STEPS):
        for a in by_app.get(tutorial_family(f), []):
            maps.setdefault(a["tag"], [0] * len(TUTORIAL_STEPS))[j] += cut(a["daily"])
    front = maps.pop(TUTORIAL_FRONT_TAG, [0] * len(TUTORIAL_STEPS))
    rows_ = sorted(([INSTANCE_NAMES.get(t, t)] + v for t, v in maps.items() if any(v)),
                   key=lambda r: (-sum(r[1:]), r[0]))
    unnamed = [totals[j] - front[j] - sum(r[j + 1] for r in rows_)
               for j in range(len(TUTORIAL_STEPS))]
    if any(n < 0 for n in unnamed):
        fail("first-visit help: the maps' and the front page's presses add up to "
             "more than a step's total (%s and %s against %s). The fetcher keeps "
             "them from the same rows."
             % ([sum(r[j + 1] for r in rows_) for j in range(len(totals))], front, totals))
    in_play = full.get("event_in_play")
    play = None if in_play is None else [
        cut(in_play[tutorial_family(f)]["daily"]) if tutorial_family(f) in in_play else 0
        for f, _ in TUTORIAL_STEPS]
    hp = full.get("help_page")
    return {"steps": [label for _, label in TUTORIAL_STEPS],
            "totals": totals,
            "maps": rows_,
            "front": front if any(front) else None,
            "unnamed": unnamed if any(unnamed) else None,
            "play": play,
            "helpPage": cut(hp["daily"]) if hp else None,
            "since": long_label(TUTORIAL_FROM),
            "before": end < TUTORIAL_FROM}


def tutorial_rows(t):
    """The first-visit help table's body for one window, as the page's script
    draws it: every map with a press, the front page, the presses named for
    no map, a total, and the presses inside the Google Play app. Kept in
    step with the script's drawTutorial()."""
    fmt = "{:,}".format
    if not any(t["totals"]):
        return ['<tr><td colspan="%d">Nothing counted yet.</td></tr>'
                % (len(t["steps"]) + 1)]
    out = []
    row = lambda name, vals, cls="": (
        '<tr%s><td>%s</td>%s</tr>' % (' class="%s"' % cls if cls else "", name,
                                      "".join('<td class="num">%s</td>' % fmt(v)
                                              for v in vals)))
    for r in t["maps"]:
        out.append(row(escape_html(r[0]), r[1:]))
    if t["front"]:
        out.append(row("Front page", t["front"]))
    if t["unnamed"]:
        out.append(row("Map not recorded<small>pressed before each count named "
                       "its map</small>", t["unnamed"]))
    out.append(row("In all", t["totals"], "total"))
    if t["play"] is not None:
        out.append(row("In the Google Play app<small>in the rows above as "
                       "well</small>", t["play"]))
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
            "return": v["return"], "frontSince": long_label(VISIT_FRONT_FROM),
            "byApp": [[VISIT_FRONT_NAME if r["tag"] == VISIT_FRONT_TAG
                       else INSTANCE_NAMES.get(r["tag"], r["tag"]), r["count"]]
                      for r in v["by_app_return"]]}


def page_rank(pg, path):
    """A page's place in its window's pages list, by pages viewed: 1 plus the
    pages viewed more often, so a tie shares a place. None when the page is
    not in the list, which holds the window's top 20, so its count and place
    are unknown rather than zero. The school board sentence said "the fourth
    most of any page" by hand in every timeframe until 2026-10-27, when it was
    fourth over two months and eleventh over the last seven days."""
    if path not in pg:
        return None
    return 1 + sum(1 for c in pg.values() if c > pg[path])


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
    ml_sources, ml_results, ml_places, ml = map_link_summary(gc, start)
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
                "results": u["results"], "tutorial": u["tutorial"]},
        # The first-visit help, counted apart from what readers do with the
        # map. See TUTORIAL_PREFIX.
        "tutorial": tutorial_use(full, days, end),
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
                "school": pg.get("/il/school-board.html", 0),
                "schoolRank": page_rank(pg, "/il/school-board.html")},
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


# ---- milestones --------------------------------------------------------------
# The Milestones tab, added 2026-10-27 for the two things Adam asked the report
# to watch: whether people are getting answers, and what the figures can show a
# state's officials. Unlike the rest of the page, the tab is plain HTML written
# here whole, between TRAFFIC-MILESTONES markers, sentences included: every one
# of them is built from a figure, so none can outlive its number, and a reader
# with no JavaScript and a crawler read exactly what a browser shows.
MS_BEGIN = "<!-- ==== TRAFFIC-MILESTONES:BEGIN ==== -->"
MS_END = "<!-- ==== TRAFFIC-MILESTONES:END ==== -->"
# The day each mark was first passed, kept because the figures behind it roll:
# the daily series reaches back two months and the per-map and visit figures
# are a single 30-day total, so a date found today would be gone in a few weeks.
# APPEND-ONLY. A mark once recorded keeps its date even when the figure falls
# back under it; a date is never moved and an entry never removed.
MILESTONE_FILE = os.path.join(ROOT, "data", "traffic-milestones.json")
# The first day of the figures this record was started from. A mark already
# passed on that day may have been passed before it, so its date reads "by".
MILESTONES_FROM = "2026-08-26"
# SET AHEAD AND NEVER LOWERED, on 2026-10-27. A mark moved down to be reached
# says nothing; when the last one is passed, add a higher one.
POINT_MONTH_MARKS = (1000, 2500, 5000, 10000)
POINT_DAY_MARKS = (100, 250, 500, 1000)
VISIT_MONTH_MARKS = (2500, 5000, 10000, 25000)
MAP_MONTH_MARKS = (100, 500, 1000, 5000)
# Every live map at once: a state that has just gone live holds this back,
# which is the point of it, since officials ask about their own state.
EVERY_MAP_MARKS = (100, 500, 1000)
# The day the maps began sending a chosen point under their own tag
# (`select/il`); before it, `select` was one path for every map, so no map's
# own count reaches further back.
POINTS_BY_MAP_FROM = "2026-10-27"


def load_milestones():
    if not os.path.exists(MILESTONE_FILE):
        return {"reached": {}}
    with open(MILESTONE_FILE, encoding="utf-8") as f:
        doc = json.load(f)
    if not isinstance(doc.get("reached"), dict):
        fail("%s carries no `reached` object"
             % os.path.relpath(MILESTONE_FILE, ROOT))
    return doc


def milestone_json(record):
    doc = {"_comment": (
        "Written by scripts/build_traffic_page.py: the day each traffic "
        "milestone was first passed, for traffic.html's Milestones tab. "
        "Append-only; a recorded date is never moved. exact is false where the "
        "figure is not kept day by day, so the date is the first refresh that "
        "found the mark passed and reads 'by'."),
        "reached": dict(sorted(record["reached"].items()))}
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def first_day_at(dates, series, mark):
    """The first day a one-day figure reached `mark`, or None. The first day
    of the figures may have had others like it before: not exact."""
    for i, v in enumerate(series):
        if v >= mark:
            return {"date": dates[i], "exact": i > 0}
    return None


def first_rolling_at(dates, series, n, mark):
    """The first day the sum of the `n` days ending on it reached `mark`, or
    None. The first day with `n` days behind it is not exact, for the same
    reason."""
    for i in range(n - 1, len(series)):
        if sum(series[i - n + 1:i + 1]) >= mark:
            return {"date": dates[i], "exact": i > n - 1}
    return None


def milestones(gc, record):
    """The Milestones tab's HTML, the record with any mark newly passed, and a
    line per mark newly passed for the run's printout."""
    fmt = "{:,}".format
    reached = dict(record["reached"])
    new = []
    dates = [d["date"] for d in gc["daily"]]
    end = gc["window"]["end"]
    rows_ = daily_rows(gc)
    points = [r[4] for r in rows_]
    w30 = gc.get("windows", {}).get("30")
    if not w30:
        fail("the data file carries no 30-day window, which the Milestones "
             "tab reads. Run the fetch workflow again.")

    def remember(key, found, what):
        if key not in reached and found:
            reached[key] = found
            new.append("%s: %s passed, %s%s" % (
                what, fmt(int(key.rsplit("/", 1)[1])),
                "" if found["exact"] else "by ", found["date"]))

    def when(entry):
        return ("" if entry["exact"] else "by ") + label(entry["date"])

    def ladder(prefix, marks, name=fmt):
        """The marks as list items, and the first not yet passed."""
        out, nxt = [], None
        for m in marks:
            hit = reached.get("%s/%d" % (prefix, m))
            if hit:
                out.append('<li class="passed"><span class="mark">%s</span> '
                           'passed %s</li>' % (name(m), when(hit)))
            elif nxt is None:
                nxt = m
                out.append('<li class="next"><span class="mark">%s</span></li>'
                           % name(m))
            else:
                out.append('<li><span class="mark">%s</span></li>' % name(m))
        return out, nxt

    def box(title, value, to, width, items):
        return "\n".join([
            '<div class="mile">',
            '          <h4>%s</h4>' % title,
            '          <p class="now"><span class="value">%s</span>'
            '<span class="to">%s</span></p>' % (value, to),
            '          <div class="meter" aria-hidden="true"><div class="fill" '
            'style="width:%d%%"></div></div>' % width,
            '          <ol class="marks">',
            "\n".join("            " + li for li in items),
            '          </ol>',
            '        </div>'])

    def card(title, value, after, prefix, marks):
        items, nxt = ladder(prefix, marks)
        if nxt is None:
            to, width = "every mark passed", 100
        else:
            to = "%s to go to %s" % (fmt(max(0, nxt - value)), fmt(nxt))
            width = min(100, jsround(value / nxt * 100))
        return box(title, fmt(value), after + to, width, items)

    # People getting answers: points chosen over the last 30 days, and on the
    # best single day of the two months the figures cover.
    for m in POINT_MONTH_MARKS:
        remember("points-30/%d" % m, first_rolling_at(dates, points, 30, m),
                 "Points chosen in 30 days")
    for m in POINT_DAY_MARKS:
        remember("points-day/%d" % m, first_day_at(dates, points, m),
                 "Points chosen in one day")
    best = max(range(len(points)), key=lambda i: (points[i], -i))
    answers = [
        card("Points chosen in the last 30 days", sum(points[-30:]), "",
             "points-30", POINT_MONTH_MARKS),
        card("Most points chosen in one day", points[best],
             "on %s; " % long_label(dates[best]), "points-day",
             POINT_DAY_MARKS),
    ]

    # For officials: visits to every map together, then each map's pages.
    visits = people(w30, rows_[-30:])["visits"]
    for m in VISIT_MONTH_MARKS:
        remember("visits-30/%d" % m,
                 {"date": end, "exact": False} if visits >= m else None,
                 "Visits in 30 days")
    reach = card("Visits in the last 30 days, every map together", visits, "",
                 "visits-30", VISIT_MONTH_MARKS)

    pages30 = {r["key"]: r["count"] for r in w30["instances"]}
    live = [t for t in fleet_tags() if FLEET_LISTED[t] <= end]
    # Each map's points chosen over the same 30 days, once the file carries
    # the per-map series (goatcounter_fetch.py, since 2026-10-27) AND that
    # series has a map in it. A fetch whose window ends before the first
    # select/<tag> was sent carries an empty list, and a column of zeros
    # beside maps where hundreds of points were chosen would read as none.
    by_app = gc.get("event_by_app", {}).get("select")
    points30 = ({a["tag"]: sum(a["daily"][-30:]) for a in by_app}
                if by_app else None)
    table = []
    for t in sorted(live, key=lambda t: (-pages30.get(t, 0), INSTANCE_NAMES[t])):
        n = pages30.get(t, 0)
        key = lambda m: "map-pages-30/%s/%d" % (t, m)
        for m in MAP_MONTH_MARKS:
            remember(key(m), {"date": end, "exact": False} if n >= m else None,
                     "%s pages viewed in 30 days" % INSTANCE_NAMES[t])
        passed = [m for m in MAP_MONTH_MARKS if key(m) in reached]
        nxt = next((m for m in MAP_MONTH_MARKS if key(m) not in reached), None)
        name = INSTANCE_NAMES[t]
        if FLEET_LISTED[t] > w30["start"]:
            age = (datetime.date.fromisoformat(end)
                   - datetime.date.fromisoformat(FLEET_LISTED[t])).days + 1
            name += " <small>live %d day%s</small>" % (age, "" if age == 1 else "s")
        top = ("%s <small>%s</small>" % (fmt(passed[-1]), when(reached[key(passed[-1])]))
               if passed else "&mdash;")
        nx = ("%s <small>%s to go</small>" % (fmt(nxt), fmt(max(0, nxt - n)))
              if nxt else "every mark passed")
        # Last, so the marks sit beside the pages figure they are marks of.
        pts = ('<td class="num mk">%s</td>' % fmt(points30.get(t, 0))
               if points30 is not None else "")
        table.append('<tr><td>%s</td><td class="num">%s</td><td class="mk">%s</td>'
                     '<td>%s</td>%s</tr>' % (name, fmt(n), top, nx, pts))
    for m in EVERY_MAP_MARKS:
        remember("every-map-30/%d" % m,
                 {"date": end, "exact": False}
                 if all(pages30.get(t, 0) >= m for t in live) else None,
                 "Every map's pages viewed in 30 days")
    items, nxt = ladder("every-map-30", EVERY_MAP_MARKS, lambda m: fmt(m) + " each")
    aim = nxt or EVERY_MAP_MARKS[-1]
    over = sum(1 for t in live if pages30.get(t, 0) >= aim)
    every = box("Maps past %s pages viewed in the last 30 days" % fmt(aim),
                "%s <small>of %s</small>" % (fmt(over), fmt(len(live))),
                "every mark passed" if nxt is None else
                "%s more to go" % fmt(len(live) - over),
                jsround(over / len(live) * 100) if live else 0, items)

    caption = "Each map in the last 30 days"
    if points30 is not None and w30["start"] < POINTS_BY_MAP_FROM:
        caption += (" <small>Points chosen are counted map by map from %s, so "
                    "they cover fewer days than the pages.</small>"
                    % (long_label(POINTS_BY_MAP_FROM) + ", " + POINTS_BY_MAP_FROM[:4]))
    read_on = datetime.date.fromisoformat(gc["fetched"][:10]).strftime("%B %-d, %Y")
    html = "\n".join([
        MS_BEGIN,
        '    <!-- GENERATED by scripts/build_traffic_page.py from the three data '
        'files and data/traffic-milestones.json. Do not hand-edit: rerun the '
        'script. -->',
        '    <section class="ruled milestones">',
        '      <div class="sec-head">',
        '        <h2>Milestones</h2>',
        '        <span class="window-note">Figures through %s, read on %s</span>'
        % (long_label(end) + ", " + end[:4], read_on),
        '      </div>',
        '      <p class="take">Marks to watch for, in two groups: people getting '
        'answers, and figures worth showing a state&rsquo;s officials. A mark '
        'passed shows the day it was first reached.</p>',
        '',
        '      <h3 class="kicker">People getting answers</h3>',
        '      <p class="take">Choosing a point is when someone gets an answer: '
        'the map then names every district at that spot and who holds each '
        'seat.</p>',
        '      <div class="miles">',
        '        ' + "\n        ".join(answers),
        '      </div>',
        '',
        '      <h3 class="kicker">Figures for state officials</h3>',
        '      <p class="take">How much the maps were used in the last 30 days, '
        'all together and one by one, for a letter or a meeting.</p>',
        '      <div class="miles">',
        '        ' + reach,
        '        ' + every,
        '      </div>',
        '      <div class="tablecard">',
        '        <table class="q" id="mapMarks">',
        '          <caption>%s</caption>' % caption,
        '          <thead><tr><th scope="col">Map</th><th scope="col" '
        'class="num">Pages viewed</th><th scope="col" class="mk">Passed</th>'
        '<th scope="col">Next mark</th>%s</tr></thead>'
        % ('<th scope="col" class="num mk">Points chosen</th>'
           if points30 is not None else ""),
        '          <tbody>',
        "\n".join("            " + r for r in table),
        '          </tbody>',
        '        </table>',
        '      </div>',
        '    </section>',
        '',
        '    <section class="ruled notes">',
        '      <h2>How the marks are counted</h2>',
        '      <ol>',
        '        <li><strong>Points chosen.</strong> A point is counted once a '
        'visit, so someone who checks three addresses in one visit counts once, '
        'and these figures are a floor. Until %s the counter did not say '
        'which state&rsquo;s map a point was chosen on. Since then each map '
        'counts its own, %s, and someone who uses two maps in one visit counts '
        'once on each.</li>'
        % (long_label(POINTS_BY_MAP_FROM) + ", " + POINTS_BY_MAP_FROM[:4],
           "which the table shows" if points30 is not None else
           "which the table will show once a refresh has read it"),
        '        <li><strong>The dates.</strong> Points chosen are kept day by '
        'day, so their dates are the day the mark was reached. Visits and each '
        'map&rsquo;s pages are kept only as a total for the last 30 days, so '
        'their dates are the first daily refresh that found the mark passed, '
        'and read &ldquo;by&rdquo;. The record begins with the figures for %s, '
        'and a mark already passed then reads &ldquo;by&rdquo; too.</li>'
        % (long_label(MILESTONES_FROM) + ", " + MILESTONES_FROM[:4]),
        '        <li><strong>Each map.</strong> Pages viewed counts every page '
        'under a state&rsquo;s address: its map, its question pages and its '
        'county pages. It counts readers from anywhere, so someone in Indiana '
        'looking up an Illinois address counts for Illinois. A map that went '
        'live during the 30 days says how many days it has had.</li>',
        '        <li><strong>The marks.</strong> They were set on October 27, '
        '2026, and are never lowered to be reached. Once the last is passed, a '
        'higher one is added.</li>',
        '      </ol>',
        '    </section>',
        '    ' + MS_END])
    return html, {"reached": reached}, new


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
     searches and location requests, other actions, then the three kinds of
     event that are NOT a reader doing something with the map: automatic
     counts, results and presses on the first-visit help]. The first three
     add up to the day's page visits and the last seven to its events, which
     the builder checks day by day. */
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
    /* Reader actions in all, and the three kinds of event left out of them:
       the apps' own counts, results and presses on the first-visit help. */
    use: %s,
    /* The first-visit help (engine first-use, since `since`): each step's
       presses in `totals`, in the order of `steps`; one row per map with a
       press, [map, then the same steps]; `unnamed`, the presses before each
       count named its map, or null; `play`, the presses inside the Google
       Play app, which are in the rows too, or null for a file fetched
       before they were kept apart; and `helpPage`, the How to use page's
       views, which are in the pages viewed too, or null for a file fetched
       before they were kept. `before` is true for a window ending before the
       help went live. None of it is in the reader actions. */
    tutorial: %s,
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
    seo: { police: %d, school: %d, schoolRank: %s },
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
        compact(bd["tutorial"]).replace("</", "<\\/"),
        rows(bd["mapLinkSources"], 2), rows(bd["mapLinkResults"], 2),
        rows(bd["mapLinkPlaces"], 2),
        json.dumps(bd["mapLinks"], separators=(", ", ": "), sort_keys=True),
        bd["geoTries"],
        "null" if bd["geoSuccess"] is None else str(bd["geoSuccess"]),
        compact(bd["layerScope"]), compact(bd["layerSplit"]),
        compact(bd["layerPooled"]), bd["layerSplitFrom"],
        bd["seo"]["police"], bd["seo"]["school"],
        "null" if bd["seo"]["schoolRank"] is None else bd["seo"]["schoolRank"],
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
        "tutorialCount": fmt(u["tutorial"]),
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
    if MS_BEGIN not in updated or MS_END not in updated:
        fail("traffic.html carries no TRAFFIC-MILESTONES markers. Put them "
             "inside the Milestones tab's panel.")
    record = load_milestones()
    ms_html, record_after, newly = milestones(gc, record)
    head, rest = updated.split(MS_BEGIN, 1)
    _, tail = rest.split(MS_END, 1)
    updated = head + ms_html + tail
    # The first-visit help's table for the full window, which the page's
    # script redraws for whichever window is chosen; this is what a crawler
    # and a reader without JavaScript see.
    if TUTORIAL_BEGIN not in updated or TUTORIAL_END not in updated:
        fail("traffic.html carries no TRAFFIC-TUTORIAL markers. Put them inside "
             "the first-visit help table's tbody.")
    head, rest = updated.split(TUTORIAL_BEGIN, 1)
    _, tail = rest.split(TUTORIAL_END, 1)
    t_full = tutorial_use(gc, daily_rows(gc), gc["window"]["end"])
    updated = (head + TUTORIAL_BEGIN + "\n" +
               "".join("          %s\n" % r for r in tutorial_rows(t_full)) +
               "          " + TUTORIAL_END + tail)
    record_text = milestone_json(record_after)
    record_old = (open(MILESTONE_FILE, encoding="utf-8").read()
                  if os.path.exists(MILESTONE_FILE) else "")

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
    unknown = families(gc)[4]
    help_unnamed = {f: n for f, n in unknown.items() if is_tutorial(f)}
    unknown = {f: n for f, n in unknown.items() if not is_tutorial(f)}
    if unknown:
        # Counted as reader actions under "Other". Name it in ACTION_GROUPS,
        # RESULT_FAMILIES or AUTOMATIC_FAMILIES, whichever it is.
        print("UNCLASSIFIED event families, counted as reader actions: %s"
              % ", ".join("%s (%d)" % kv for kv in sorted(unknown.items())))
    if help_unnamed:
        # In the help's total and in no column of its table. A bare
        # "first-use" is a file fetched before the steps were kept apart;
        # anything else is a new step for TUTORIAL_STEPS.
        print("UNNAMED first-visit help families, in its total and no column: %s"
              % ", ".join("%s (%d)" % kv for kv in sorted(help_unnamed.items())))
    t = tutorial_use(gc, daily_rows(gc), gc["window"]["end"])
    print("first-visit help (not reader actions): %s; %s map(s) named, %s, "
          "%s on the front page, %s in the Google Play app; How to use page "
          "viewed %s"
          % (", ".join("%s %d" % kv for kv in zip(t["steps"], t["totals"])),
             len(t["maps"]),
             "none unnamed" if not t["unnamed"] else "%d unnamed" % sum(t["unnamed"]),
             sum(t["front"] or [0]),
             "unknown" if t["play"] is None else sum(t["play"]),
             "unknown" if t["helpPage"] is None else t["helpPage"]))
    print("  %d data-stat span(s) written from the data; %d key(s) keep a "
          "hand-typed fallback a crawler reads: %s"
          % (len(fallbacks), len(unwritten), ", ".join(sorted(unwritten)) or "none"))
    # A mark newly passed is news for the day's reply, so it is printed in
    # words a reply can carry. Nothing is printed on a day with none.
    for line in newly:
        print("MILESTONE %s" % line)

    if args.check:
        print("build-traffic-page: %s"
              % ("current" if updated == page and record_text == record_old
                 else "WOULD CHANGE — rerun without --check"))
        return
    if record_text != record_old:
        with open(MILESTONE_FILE, "w", encoding="utf-8") as f:
            f.write(record_text)
        print("build-traffic-page: wrote %s"
              % os.path.relpath(MILESTONE_FILE, ROOT))
    if updated == page:
        print("build-traffic-page: OK — no change")
        return
    with open(PAGE, "w", encoding="utf-8") as f:
        f.write(updated)
    print("build-traffic-page: wrote %s — now READ THE PROSE, which this "
          "script does not touch" % os.path.relpath(PAGE, ROOT))


if __name__ == "__main__":
    main()
