#!/usr/bin/env python3
"""
Which analytics host each page loads, held to the worksheet that declares it.

WHY THIS EXISTS. `brand.analytics` in an instance's worksheet is the one place
that says whether it runs Google Analytics, and `generate_metro_files.py` emits
the tag from it into a GENERATED region — in that instance's `index.html` and
nowhere else. Every sub-page's tag was a HAND-WRITTEN COPY, and copies drift in
the direction copies always drift: measured 2026-09-15, `ca/sources.html` and
`wi/sources.html` loaded Google Analytics into Chicago's property while their
own apps declare no `ga_id` at all, because both pages were cloned from
Illinois's. Nothing compared them — `build_privacy_page.py` measures each app's
own `index.html`, which is the right subject for what it publishes and cannot
see a sub-page.

It also cost every reader of a content page 175 KB. `gtag.js` was about 69% of
`il/county-board.html`'s payload beside a 3 KB cookieless counter, on thirteen
pages that do not draw a map.

THE RULE, in two halves:

  GOOGLE ANALYTICS belongs to the two apps whose worksheets declare a `ga_id`,
  in their `index.html`, where the generator puts it. Anywhere else it is a copy.
  Dropping it from the thirteen cost no measurement this project reports on:
  GoatCounter is on all of them and is what data/goatcounter-traffic.json and
  the traffic report read.

  GOATCOUNTER belongs to every page, and 193 of 245 carried none when this gate
  was written — all 183 per-county pages, the four history pages and six root
  pages. The traffic report's subject is what this fleet gets read, and it had
  never counted the largest page set on the site: the 183 pages carrying 2,869
  officeholders. Adding a counter changes what those pages send, so it waited on
  the operator, who said to count them; 191 pages gained the tag on 2026-09-15
  and the two deliberate exceptions are named below.

  THE TAG NOW HAS ONE COPY, engine/shared/goatcounter.txt, read by every
  generated page's builder and spliced as an ENGINE fence into the authored ones
  — the two mechanisms engine/shared/footer-byline.txt already uses. This holds
  every worksheet's `brand.analytics.goatcounter_url` to the URL in that file, so
  a rename there cannot leave an instance reporting somewhere else.

    python3 scripts/validate_analytics.py
"""

import glob
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GA_HOST = "googletagmanager.com/gtag/js"
# THE TAG, NOT THE HOST. Matching the string `goatcounter.com/count` anywhere on
# a page credited /privacy.html for naming that URL in its own recipients TABLE,
# as documentation, while carrying no counter at all — a gate that greps for a
# host rewards a page for describing it. So this looks for the script.
GC_TAG = re.compile(r'<script[^>]+data-goatcounter=', re.I)
# The URL every worksheet must agree on, read from the one copy of the tag.
GC_BLOCK = os.path.join(REPO_ROOT, "engine", "shared", "goatcounter.txt")

# HOW MANY PAGES CARRY NO COUNTER, held so the number cannot move unnoticed.
# It was 193 when this gate was written and every one of them is now NAMED: the
# operator's answer on 2026-09-15 was to count the other 191, so the gap is the
# two deliberate exceptions below and nothing else.
COUNTER_GAP = 2
COUNTER_GAP_MEASURED = "2026-09-15"

# The two that are deliberate, with the reason. The gate fails on a third, in
# either direction: a page that shipped uncounted, or one of these two that
# gained a counter.
NO_COUNTER = {
    "coverage-map.html": dict(
        date="2026-09-15",
        reason="the landing page's iframe body, not a destination. It is not in "
               "the sitemap and a reader never lands on it directly, so a "
               "second count of the same visit is all a counter would add."),
    "404.html": dict(
        date="2026-09-15",
        reason="served for a URL that does not exist. Counting it would put "
               "other people's broken links in the traffic report as pages."),
}
# The root redirect shells the R2.3 move left behind: a meta refresh and nothing
# else. A counter on one would count a visit the destination counts a moment
# later.
REDIRECT_SHELL = re.compile(r'<meta[^>]+http-equiv=["\']refresh', re.I)


def fail(msgs):
    for m in msgs:
        print("validate-analytics: FAIL — %s" % m, file=sys.stderr)
    sys.exit(1)


def instances():
    """A top-level directory with an index.html and a data/app — the same rule
    validate_card_links.py and validate_instance_registration.py discover by."""
    out = []
    for name in sorted(os.listdir(REPO_ROOT)):
        if (os.path.isdir(os.path.join(REPO_ROOT, name, "data", "app"))
                and os.path.exists(os.path.join(REPO_ROOT, name, "index.html"))):
            out.append(name)
    return out


def ga_id(tag):
    rel = "metro-worksheet.json" if tag == "il" else "%s/metro-worksheet.json" % tag
    path = os.path.join(REPO_ROOT, rel)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        w = json.load(f)
    return ((w.get("brand") or {}).get("analytics") or {}).get("ga_id")


def pages():
    tags = instances()
    out = []
    for path in sorted(glob.glob(os.path.join(REPO_ROOT, "*.html"))):
        out.append((None, os.path.basename(path), path))
    for tag in tags:
        for path in sorted(glob.glob(os.path.join(REPO_ROOT, tag, "*.html"))):
            out.append((tag, "%s/%s" % (tag, os.path.basename(path)), path))
        for sub in ("county-board", "county-supervisor", "county-commissioner"):
            for path in sorted(glob.glob(os.path.join(REPO_ROOT, tag, sub, "*.html"))):
                out.append((tag, os.path.relpath(path, REPO_ROOT), path))
    return out, tags


def main():
    surface, tags = pages()
    if len(tags) < 2:
        fail(["found %d instance(s); the tree walk is wrong" % len(tags)])
    with open(GC_BLOCK, encoding="utf-8") as f:
        block = f.read()
    m = re.search(r'data-goatcounter="([^"]+)"', block)
    if not m:
        fail(["%s carries no data-goatcounter URL — it is the one copy of the "
              "tag and every page reads it"
              % os.path.relpath(GC_BLOCK, REPO_ROOT)])
    gc_url = m.group(1)

    declared = {t: ga_id(t) for t in tags}
    problems, ga_pages, no_counter, shells, uncounted = [], [], [], [], []
    for tag in tags:
        rel = ("metro-worksheet.json" if tag == "il"
               else "%s/metro-worksheet.json" % tag)
        with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as f:
            url = (((json.load(f).get("brand") or {}).get("analytics") or {})
                   .get("goatcounter_url"))
        if url != gc_url:
            problems.append(
                "%s declares goatcounter_url %r and the one copy of the tag "
                "sends to %r. Every surface reports to one site and the path "
                "tells them apart, so these cannot differ." % (rel, url, gc_url))

    for tag, rel, path in surface:
        with open(path, encoding="utf-8") as f:
            src = f.read()
        has_ga = GA_HOST in src
        has_gc = bool(GC_TAG.search(src))
        shell = bool(REDIRECT_SHELL.search(src))

        if has_ga:
            ga_pages.append(rel)
            expected = tag and declared.get(tag) and rel == "%s/index.html" % tag
            if not expected:
                why = ("its instance declares no ga_id" if not (tag and declared.get(tag))
                       else "the worksheet puts the tag in %s/index.html and "
                            "nowhere else" % tag)
                problems.append(
                    "%s loads Google Analytics and %s. The tag is GENERATED from "
                    "brand.analytics into an app's index.html; a copy anywhere "
                    "else is a hand-written claim nothing checks — and two pages "
                    "were reporting into another instance's property. Delete the "
                    "block." % (rel, why))

        if shell:
            shells.append(rel)
            continue
        if not has_gc:
            uncounted.append(rel)
            entry = NO_COUNTER.get(rel)
            if entry:
                no_counter.append((rel, entry))

    if len(uncounted) != COUNTER_GAP:
        by_group = {}
        for rel in uncounted:
            if "/" not in rel:
                key = "root pages"
            else:
                tag, rest = rel.split("/", 1)
                key = "%s/%s" % (tag, "sub-pages" if "/" not in rest
                                 else "per-county pages")
            by_group[key] = by_group.get(key, 0) + 1
        problems.append(
            "%d page(s) carry no counter and COUNTER_GAP records %d, measured "
            "%s. %s — either a page shipped uncounted or somebody closed part "
            "of the gap; move the number either way so it keeps describing the "
            "tree. Now: %s"
            % (len(uncounted), COUNTER_GAP, COUNTER_GAP_MEASURED,
               "It went UP" if len(uncounted) > COUNTER_GAP else "It went DOWN",
               "; ".join("%s %d" % (k, v) for k, v in sorted(by_group.items()))))

    for rel, entry in sorted(NO_COUNTER.items()):
        path = os.path.join(REPO_ROOT, rel)
        if not os.path.exists(path):
            problems.append("NO_COUNTER records %s (%s) and that page is not in "
                            "the tree — drop the entry" % (rel, entry["date"]))
            continue
        with open(path, encoding="utf-8") as f:
            if GC_TAG.search(f.read()):
                problems.append(
                    "NO_COUNTER records %s (%s) as deliberately uncounted and it "
                    "now loads GoatCounter — drop the entry"
                    % (rel, entry["date"]))

    if problems:
        fail(problems)
    for rel, entry in sorted(no_counter):
        print("validate-analytics: ~ %s carries no counter (%s): %s"
              % (rel, entry["date"], entry["reason"]))
    undecided = len(uncounted) - len(no_counter)
    print("validate-analytics: OK — %d page(s) across %d instance(s), %d "
          "redirect shell(s) skipped. Google Analytics on %d (%s), from the two "
          "worksheets that declare it. GoatCounter on %d from one copy of the "
          "tag; %d carry none, %d of those recorded with a reason%s"
          % (len(surface), len(tags), len(shells), len(ga_pages),
             ", ".join(ga_pages) or "none",
             len(surface) - len(shells) - len(uncounted), len(uncounted),
             len(no_counter),
             "" if not undecided else
             " and %d awaiting a decision" % undecided))


if __name__ == "__main__":
    main()
