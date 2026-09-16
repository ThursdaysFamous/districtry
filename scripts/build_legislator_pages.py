#!/usr/bin/env python3
"""
The legislator pages: twelve generated pages naming 1,058 officeholders.

WHY. Every one of the six apps already carries its state's two legislative
chambers and its U.S. House districts, with a named member on each card — 1,058
people across eighteen shipped rosters. Measured 2026-09-15, not one of them
appeared in any served byte of this site, and the site had no page at all for
"who is my state representative" or "who is my congressman", which search
results split by state and by office. build_county_pages.py closed that for
county seats and build_officeholder_tables.py for three city councils; this is
the same absence one tier up.

TWO PAGES PER INSTANCE, NOT THREE. The state's two chambers share one page
because a reader asking "who is my state legislator" wants both halves of the
answer and they are elected from different maps over the same ground; the U.S.
House gets its own because it is a different government. A page per chamber
would have split 177 Illinois names across two pages that each answer half a
question.

WHAT IS GENERATED AND WHAT IS PRESERVED. This script owns the page: its head,
its prose, its links, its structure. It does NOT own the four blocks other
generators fill, and it splices them back from the file on disk on every run —
the two ENGINE fences compose_app.py writes, the address box
build_question_forms.py writes, and the officeholder tables
build_officeholder_tables.py writes. A page created by this script carries those
markers EMPTY; the other generators fill them on their own next run, and this
script never clobbers what they wrote. That makes the four `--check`s
order-independent.

NOTHING HERE STATES A SEAT COUNT. "Illinois has 118 House districts" is the kind
of sentence that goes stale in a reapportionment and is never re-read; every
count on these pages is `len(roster)` at build time. What IS stated is the
layer id each page's map link opens, and it is stated because it cannot be
derived — so it is checked against the instance's own worksheet, and a page
naming a layer its app does not register fails the build.

    python3 scripts/build_legislator_pages.py           # write the pages
    python3 scripts/build_legislator_pages.py --check   # drift gate for CI
"""

import argparse
import difflib
import html
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from question_page import (METROS, PageError, check_layer, head, load,  # noqa: E402
                           MARK_RE, preserved_from_disk, shared_head_block,
                           shell, THEMEBOOT_RE)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Per instance: the worksheet, and the two pages' wording. `layer` is the id the
# page's map link switches on and is VERIFIED against the worksheet's layers[].
# `chambers` is upper house first, because that is the order both a ballot and
# every one of these states' own legislature websites use.
INSTANCES = {
    "il": dict(
        worksheet="metro-worksheet.json",
        legislature=dict(
            file="state-legislature.html",
            title="Who is my Illinois state legislator?",
            body="the Illinois General Assembly",
            short="Illinois General Assembly",
            term="Senators serve staggered two- and four-year terms and "
                 "representatives two-year terms.",
            chambers=[
                dict(layer="il-senate", name="Illinois Senate", short="Senate",
                     holder="Senator", roster="il-senate-members.json"),
                dict(layer="il-house", name="Illinois House of Representatives", short="House",
                     holder="Representative", roster="il-house-members.json"),
            ]),
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="congress", roster="congress-roster.json",
            state="Illinois"),
    ),
    "ny": dict(
        worksheet="ny/metro-worksheet.json",
        legislature=dict(
            file="state-legislature.html",
            title="Who is my NY state legislator?",
            body="the New York State Legislature",
            short="New York State Legislature",
            term="Both chambers run on two-year terms.",
            chambers=[
                dict(layer="state-senate", name="New York State Senate", short="Senate",
                     holder="Senator", roster="ny-senate-members.json"),
                dict(layer="state-assembly", name="New York State Assembly", short="Assembly",
                     holder="Assembly Member", roster="ny-assembly-members.json"),
            ]),
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="congress", roster="congress-roster.json",
            state="New York"),
    ),
    "ca": dict(
        worksheet="ca/metro-worksheet.json",
        legislature=dict(
            file="state-legislature.html",
            title="Who is my CA state legislator?",
            body="the California State Legislature",
            short="California State Legislature",
            term="Senators serve four-year terms and Assembly members two.",
            chambers=[
                dict(layer="ca-senate", name="California State Senate", short="Senate",
                     holder="Senator", roster="ca-senate-members.json"),
                dict(layer="ca-assembly", name="California State Assembly", short="Assembly",
                     holder="Assembly Member", roster="ca-assembly-members.json"),
            ]),
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="congress", roster="congress-roster.json",
            state="California"),
    ),
    "wi": dict(
        worksheet="wi/metro-worksheet.json",
        legislature=dict(
            file="state-legislature.html",
            title="Who is my Wisconsin legislator?",
            body="the Wisconsin Legislature",
            short="Wisconsin Legislature",
            term="Senators serve four-year terms and Assembly members two.",
            chambers=[
                dict(layer="wi-senate", name="Wisconsin State Senate", short="Senate",
                     holder="Senator", roster="wi-senate-members.json"),
                dict(layer="wi-assembly", name="Wisconsin State Assembly", short="Assembly",
                     holder="Representative", roster="wi-assembly-members.json"),
            ]),
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="us-house", roster="congress-roster.json",
            state="Wisconsin"),
    ),
    "ia": dict(
        worksheet="ia/metro-worksheet.json",
        legislature=dict(
            file="state-legislature.html",
            title="Who is my Iowa legislator?",
            body="the Iowa General Assembly",
            short="Iowa General Assembly",
            term="Senators serve four-year terms and representatives two.",
            chambers=[
                dict(layer="ia-senate", name="Iowa Senate", short="Senate",
                     holder="Senator", roster="ia-senate-members.json"),
                dict(layer="ia-house", name="Iowa House of Representatives", short="House",
                     holder="Representative", roster="ia-house-members.json"),
            ]),
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="us-house", roster="congress-roster.json",
            state="Iowa"),
    ),
    "mi": dict(
        worksheet="mi/metro-worksheet.json",
        legislature=dict(
            file="state-legislature.html",
            title="Who is my Michigan legislator?",
            body="the Michigan Legislature",
            short="Michigan Legislature",
            term="Senators serve four-year terms and representatives two.",
            chambers=[
                dict(layer="mi-senate", name="Michigan Senate", short="Senate",
                     holder="Senator", roster="mi-senate-members.json"),
                dict(layer="mi-house", name="Michigan House of Representatives", short="House",
                     holder="Representative", roster="mi-house-members.json"),
            ]),
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="us-house", roster="congress-roster.json",
            state="Michigan"),
    ),
}


def fail(msg):
    print("build-legislator-pages: FAIL — %s" % msg, file=sys.stderr)
    sys.exit(1)


def roster_rows(tag, filename):
    data = load(os.path.join(tag, "data", "app", filename))
    if not isinstance(data, dict) or not data:
        fail("%s/data/app/%s is not a non-empty object" % (tag, filename))
    named = [k for k, v in data.items() if isinstance(v, dict) and v.get("name")]
    if not named:
        fail("%s/data/app/%s names nobody" % (tag, filename))
    return data


def legislature_page(tag, inst, worksheet, brand, app_name, landing, metros):
    spec = inst["legislature"]
    counts = []
    for ch in spec["chambers"]:
        check_layer(worksheet, ch["layer"], "%s/%s" % (tag, spec["file"]))
        counts.append(len(roster_rows(tag, ch["roster"])))
    layers = ",".join(ch["layer"] for ch in spec["chambers"])
    total = sum(counts)
    # "59 Senate districts and 118 House districts", not "59 Illinois Senate
    # districts, 118 Illinois House of Representatives districts" — the state is
    # already in the body's name two words earlier, and a list joined with a
    # comma and no conjunction reads as a fragment.
    parts = ["%d %s district%s" % (n, ch["short"], "" if n == 1 else "s")
             for n, ch in zip(counts, spec["chambers"])]
    pieces = " and ".join(parts)
    lede = dict(
        html='<p class="lede"><strong>The %s has %s.</strong> Both are drawn over the '
             'same ground and neither follows a city, county or ZIP boundary, so the '
             'only way to know which pair covers an address is to put the address on '
             'the map. %s</p>'
             % (html.escape(spec["short"]), html.escape(pieces),
                html.escape(spec["term"])),
        cta='    <a class="cta" href="./#layers=%s">Find your %s districts →</a>\n'
            '    <p class="cta-note">Opens the map with both chambers on. Search your '
            'address or ZIP, or tap your location.</p>'
            % (layers, html.escape(spec["short"])))
    sections = """  <section>
    <h2>What the lookup shows</h2>
    <div class="answer-card">
      <p>Select any point and the two cards name the <strong>district number</strong> for each
        chamber and the <strong>member</strong> who holds that seat, with their party, their
        offices and a link to their own page where the legislature publishes one.</p>
      <p>Every other district covering the same point is listed beside them, so one click answers
        the state question and the county, city and federal ones together.</p>
    </div>
  </section>

  <section>
    <h2>Two chambers, two maps</h2>
    <p>An address has one district in each chamber and the two rarely share a boundary: the
      chambers are apportioned separately, and in several of these states one chamber's districts
      are built by pairing the other's. The table below lists both in full, so a reader who knows
      their district number can look up the member without opening the map at all.</p>
  </section>

  <section>
    <h2>Where the names come from</h2>
    <p>Both rosters are re-read on a schedule from the legislature's own published member lists and
      land as a reviewed pull request; the map names no officeholder it cannot cite. A seat the
      source does not name is shown as unnamed rather than filled in.</p>
    <div class="disclaimer">
      <strong>Not for legal or official use.</strong> Boundary and roster data come from public
      sources that explicitly disclaim legal precision. Confirm district assignments and
      officeholders with the relevant government office before relying on them for anything
      official.
    </div>
  </section>

"""
    subtitle = ("%s district lookup — free, by address, ZIP, or a tap on the map."
                % spec["short"])
    # Under 155 characters, which validate_serp_lengths.py holds every page to:
    # the first draft ran to 164 on the four longest body names, and a
    # description that overruns is cut mid-clause in the search result.
    desc = ("Your %s districts by address or ZIP \u2014 the district number in each "
            "chamber and the member who holds it." % spec["short"])
    og = ("Find your %s districts by address or ZIP, and the %d members who hold them."
          % (spec["short"], total))
    return spec["file"], spec["title"], subtitle, desc, og, lede, sections, total


def congress_page(tag, inst, worksheet, brand, app_name, landing, metros):
    spec = inst["congress"]
    check_layer(worksheet, spec["layer"], "%s/%s" % (tag, spec["file"]))
    roster = roster_rows(tag, spec["roster"])
    n = len(roster)
    state = spec["state"]
    lede = dict(
        html='<p class="lede"><strong>%s elects %d member%s of the U.S. House of '
             'Representatives.</strong> A congressional district is redrawn after each '
             'census to hold equal population, so it follows neither county lines nor '
             'city limits, and an address a mile away can sit in a different one.</p>'
             % (html.escape(state), n, "" if n == 1 else "s"),
        cta='    <a class="cta" href="./#layers=%s">Find your U.S. House district →</a>\n'
            '    <p class="cta-note">Opens the map with the U.S. House layer on. Search '
            'your address or ZIP, or tap your location.</p>' % spec["layer"])
    sections = """  <section>
    <h2>What the lookup shows</h2>
    <div class="answer-card">
      <p>Select any point and the card names the <strong>district number</strong> covering it and
        the <strong>representative</strong> who holds the seat, with their party, their Washington
        and district offices, and a link to their House page.</p>
      <p>Your U.S. senators are not here, and that is not an omission: senators are elected
        statewide, so every address in the state has the same two and no map can tell them apart.</p>
    </div>
  </section>

  <section>
    <h2>District, county and ZIP are three different shapes</h2>
    <p>A congressional district is an electoral boundary and nothing else. It splits counties, it
      splits cities, and it splits ZIP codes — which is why a ZIP-code lookup can return two
      representatives and be right both times. The map answers for one exact point instead.</p>
  </section>

  <section>
    <h2>Where the names come from</h2>
    <p>The boundaries come from the Census Bureau's own published districts and the roster is
      re-read on a schedule from the House's member list, landing as a reviewed pull request. The
      map names no officeholder it cannot cite.</p>
    <div class="disclaimer">
      <strong>Not for legal or official use.</strong> Boundary and roster data come from public
      sources that explicitly disclaim legal precision. Confirm district assignments and
      officeholders with the relevant government office before relying on them for anything
      official.
    </div>
  </section>

"""
    subtitle = ("%s U.S. House district lookup — free, by address, ZIP, or a tap "
                "on the map." % state)
    desc = ("Your %s U.S. House district by address or ZIP \u2014 the district number, the "
            "representative who holds it, and every other district covering that point." % state)
    og = ("Find your %s congressional district by address or ZIP, and the "
          "representative who holds it." % state)
    return spec["file"], spec["title"], subtitle, desc, og, lede, sections, n


def related_rows(tag, this_file, landing, metros):
    """Links to the instance's own map, its other new page, and one sibling.

    Derived rather than listed: the sibling is the next instance in metros.json
    order, so a new state joins these rows the day it is registered.
    """
    other = ("congress.html" if this_file != "congress.html"
             else "state-legislature.html")
    other_label = ("Who is my U.S. representative?" if other == "congress.html"
                   else "Who is my state legislator?")
    order = [m["tag"] for m in metros]
    sib = order[(order.index(tag) + 1) % len(order)]
    sib_name = next(m["landing_name"] for m in metros if m["tag"] == sib)
    sib_scope = next(m["scope"] for m in metros if m["tag"] == sib)
    esc = html.escape
    return "\n".join([
        '      <li><a href="./">What district am I in?</a><span>Every district that '
        'covers one point in %s, and who represents you there.</span></li>' % esc(landing),
        '      <li><a href="%s">%s</a><span>The other half of the answer, on its own '
        'page.</span></li>' % (other, esc(other_label)),
        '      <li><a href="../%s/">%s</a><span>The same lookup, %s.</span></li>'
        % (sib, esc(sib_name), esc(sib_scope)),
    ])


def build(tag, inst, metros, check):
    worksheet = load(inst["worksheet"])
    brand = worksheet["brand"]
    app_name = brand["app_name"]
    landing = next(m["landing_name"] for m in metros if m["tag"] == tag)
    themeboot = shared_head_block(tag, THEMEBOOT_RE, "theme boot script")
    mark = shared_head_block(tag, MARK_RE, "districtry mark")

    results = []
    for maker in (legislature_page, congress_page):
        (page_file, title, subtitle, desc, og, lede, sections,
         seats) = maker(tag, inst, worksheet, brand, app_name, landing, metros)
        path = os.path.join(REPO_ROOT, tag, page_file)
        preserved = preserved_from_disk(path)
        page = head(tag, brand, app_name, page_file, title, desc, og)
        page += shell(app_name, title, subtitle, lede, sections,
                      related_rows(tag, page_file, landing, metros), preserved,
                      themeboot, mark)
        results.append((os.path.join(tag, page_file), path, page, seats))
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="drift gate: fail rather than write")
    args = ap.parse_args()

    try:
        return run(args)
    except PageError as exc:
        fail(str(exc))


def run(args):
    metros = load(METROS)["metros"]
    known = {m["tag"] for m in metros}
    missing = set(INSTANCES) - known
    if missing:
        fail("INSTANCES names %s, which metros.json does not carry"
             % ", ".join(sorted(missing)))
    unregistered = known - set(INSTANCES)
    if unregistered:
        fail("metros.json carries %s with no entry here — every instance ships "
             "a legislature and a U.S. House layer, so a missing entry is two "
             "pages nobody wrote" % ", ".join(sorted(unregistered)))

    drift, written, seats = [], 0, 0
    for tag in sorted(INSTANCES):
        for rel, path, page, count in build(tag, INSTANCES[tag], metros, args.check):
            seats += count
            try:
                with open(path, encoding="utf-8") as f:
                    current = f.read()
            except OSError:
                current = None
            if current == page:
                continue
            if args.check:
                drift.append((rel, current, page))
                continue
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(page)
            written += 1
            print("build-legislator-pages: %s — written" % rel)

    if args.check:
        for rel, current, page in drift:
            if current is None:
                print("build-legislator-pages: %s does not exist" % rel, file=sys.stderr)
                continue
            print("build-legislator-pages: DRIFT in %s" % rel, file=sys.stderr)
            for dl in difflib.unified_diff(current.splitlines(), page.splitlines(),
                                           fromfile="committed", tofile="regenerated",
                                           lineterm="", n=1):
                print("  " + dl, file=sys.stderr)
        if drift:
            fail("%d page(s) out of date — run "
                 "python3 scripts/build_legislator_pages.py" % len(drift))
        print("build-legislator-pages: OK — %d page(s) across %d instance(s), "
              "%d officeholder(s) named" % (len(INSTANCES) * 2, len(INSTANCES), seats))
    else:
        print("build-legislator-pages: OK — %d page(s) written, %d current, "
              "%d officeholder(s) named"
              % (written, len(INSTANCES) * 2 - written, seats))


if __name__ == "__main__":
    main()
