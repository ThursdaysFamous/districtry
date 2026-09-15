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
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METROS = os.path.join(REPO_ROOT, "metros.json")
SITE = "https://districtry.com"
AUTHOR = ('{ "@type": "Person", "@id": "https://districtry.com/#author", '
          '"name": "Adam Overberg", "url": "https://overberg.co", '
          '"email": "hello@overberg.co" }')

# Regions this script writes EMPTY and never rewrites afterwards. Each is owned
# by another generator; see the module docstring.
PRESERVED = [
    ("ENGINE", "tokens-brand", "css"),
    ("ENGINE", "styles-subpage", "css"),
    ("ENGINE", "footer-byline", "html"),
    ("GENERATED", "question-lookup", "html"),
    ("GENERATED", "officeholder-table", "html"),
]

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


def load(path):
    with open(os.path.join(REPO_ROOT, path), encoding="utf-8") as f:
        return json.load(f)


def marker(kind, name, end, style):
    body = "==== %s:%s %s ====" % (kind, "END" if end else "BEGIN", name)
    return "/* %s */" % body if style == "css" else "<!-- %s -->" % body


def preserved_from_disk(path):
    """What the other four generators wrote, keyed by region name.

    A page this script has never written returns empty strings, which is how a
    new page is born with the markers present and the blocks empty.
    """
    out = {}
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return {name: "" for _k, name, _s in PRESERVED}
    for kind, name, style in PRESERVED:
        begin, end = marker(kind, name, False, style), marker(kind, name, True, style)
        if begin in text and end in text:
            i, j = text.index(begin) + len(begin), text.index(end)
            out[name] = text[i:j].strip("\n")
        else:
            out[name] = ""
    return out


def shared_head_block(tag, pattern, what):
    """The @font-face set and the theme boot script, read from this instance's
    own faq.html rather than restated here.

    Both are byte-identical across all 23 sub-pages (measured 2026-09-15), and a
    copy of a computed font override is exactly the kind of restatement
    build_brand_tokens.py exists to stop. Reading a sibling means a new page
    cannot ship with a stale one.
    """
    path = os.path.join(REPO_ROOT, tag, "faq.html")
    with open(path, encoding="utf-8") as f:
        text = f.read()
    found = re.search(pattern, text, re.S)
    if not found:
        fail("cannot find the %s in %s/faq.html — the shared sub-page head "
             "has changed shape and this generator must be updated" % (what, tag))
    return found.group(1)


FONTFACE_RE = r"(/\* Self-hosted subset.*?\n\})\n\n?/\* ==== ENGINE:BEGIN tokens-brand"
# The <script> element that carries the theme key. Matched by its CONTENT
# rather than by its opening comment: the comment is worded differently in
# every instance (measured 2026-09-15), so a pattern keyed on it finds the
# block in two instances and fails in four.
THEMEBOOT_RE = r"(<script>(?:(?!</script>).)*districtry-theme(?:(?!</script>).)*</script>)"


def roster_rows(tag, filename):
    data = load(os.path.join(tag, "data", "app", filename))
    if not isinstance(data, dict) or not data:
        fail("%s/data/app/%s is not a non-empty object" % (tag, filename))
    named = [k for k, v in data.items() if isinstance(v, dict) and v.get("name")]
    if not named:
        fail("%s/data/app/%s names nobody" % (tag, filename))
    return data


def check_layer(worksheet, layer_id, where):
    ids = {l["id"] for l in worksheet["layers"]}
    if layer_id not in ids:
        fail("%s names layer %r, which its worksheet does not register"
             % (where, layer_id))


def head(tag, meta, brand, app_name, page_file, title, description, og_desc):
    canonical = "%s/%s/%s" % (SITE, tag, page_file)
    esc = lambda s: html.escape(s, quote=True)
    jsonld = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "@id": canonical,
        "url": canonical,
        "name": "%s — %s" % (title, app_name),
        "description": description,
        "inLanguage": "en-US",
        "isPartOf": {"@id": "%s/%s/#website" % (SITE, tag)},
        "breadcrumb": {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": app_name,
                 "item": "%s/%s/" % (SITE, tag)},
                {"@type": "ListItem", "position": 2, "name": title},
            ],
        },
    }
    graph = json.dumps(jsonld, indent=2, ensure_ascii=False)
    graph = graph.replace('"inLanguage": "en-US",',
                          '"inLanguage": "en-US",\n  "author": %s,' % AUTHOR)
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />

<!-- GoatCounter — cookieless page counts, the same site this instance's app reports to. -->
<script data-goatcounter="%(gc)s"
        async src="//gc.zgo.at/count.js"></script>

<title>%(title)s — %(app)s</title>
<meta name="description" content="%(desc)s" />
<meta name="robots" content="index, follow" />
<link rel="canonical" href="%(canonical)s" />

<meta property="og:type" content="article" />
<meta property="og:site_name" content="%(app)s" />
<meta property="og:title" content="%(title)s" />
<meta property="og:description" content="%(ogdesc)s" />
<meta property="og:url" content="%(canonical)s" />
<meta property="og:image" content="%(site)s/%(tag)s/og-image.png" />
<meta property="og:image:width" content="1200" />
<meta property="og:image:height" content="630" />
<meta property="og:locale" content="en_US" />

<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="%(title)s" />
<meta name="twitter:description" content="%(ogdesc)s" />
<meta name="twitter:image" content="%(site)s/%(tag)s/og-image.png" />

<script type="application/ld+json">
%(jsonld)s
</script>

<link rel="manifest" href="manifest.webmanifest">
<meta name="theme-color" content="%(theme)s">

<link rel="icon" type="image/svg+xml" href="%(favicon)s" />

<style>
%(fontface)s
""" % dict(gc=esc(brand["analytics"]["goatcounter_url"]), title=esc(title),
           app=esc(app_name), desc=esc(description), ogdesc=esc(og_desc),
           canonical=canonical, site=SITE, tag=tag, jsonld=graph,
           theme=esc(brand["theme_color"]),
           favicon=esc(brand["favicon_data_uri"]),
           fontface=shared_head_block(tag, FONTFACE_RE, "@font-face block"))


def shell(app_name, title, subtitle, lede, sections, related,
          preserved, themeboot, mark):
    esc = html.escape
    parts = []
    # EVERY MARKER ON ITS OWN LINE. compose_app.py anchors its fence pattern to
    # the whole line, so a BEGIN/END pair sharing a line with anything else is
    # not a fence at all: the first draft emitted all four on one line, the
    # composer found no blocks in the file, reported it recomposed, and the page
    # shipped with an empty stylesheet — served in Times New Roman on a
    # transparent ground, which is what the browser gate then said.
    for kind, name, style, body in (
            ("ENGINE", "tokens-brand", "css", preserved["tokens-brand"]),
            ("ENGINE", "styles-subpage", "css", preserved["styles-subpage"])):
        parts.append(marker(kind, name, False, style) + "\n")
        if body:
            parts.append(body + "\n")
        parts.append(marker(kind, name, True, style) + "\n")
    parts.append("</style>\n")
    parts.append(themeboot)
    parts.append("""
</head>
<body>

<a href="#page-main" class="skip-link">Skip to content</a>

<header class="masthead">
  <div class="masthead-inner">
    <div class="title-block">
      <h1 class="title">
        <span class="title-row">
          %(mark)s
          <span class="title-text">%(title)s</span>
        </span>
      </h1>
      <p class="title-sub">%(subtitle)s</p>
    </div>
    <div class="masthead-actions">
      <a href="./">← Back to the map</a>
    </div>
  </div>
</header>

<main id="page-main" tabindex="-1">

  <section>
    %(lede)s
%(lookup_begin)s
%(lookup_body)s
%(lookup_end)s
%(cta)s
  </section>

%(sections)s
%(table_begin)s
%(table_body)s
%(table_end)s
  <section>
    <h2>Related lookups</h2>
    <ul class="related">
%(related)s
    </ul>
  </section>

</main>

<footer class="site-footer">
  <div class="footer-inner">
    <p>%(app)s answers one question: which civic districts contain the point you picked, and who
      represents you there. It reads public data, cites its sources, and never guesses an
      officeholder.</p>
    <div class="footer-links">
      <a href="./">← Back to the map</a>
      <a href="faq.html">Common questions</a>
      <a href="sources.html">Sources &amp; data layers</a>
      <a href="../privacy.html">Privacy</a>
      <a href="https://overberg.co/why/" target="_blank" rel="noopener">Why this exists</a>
      <a href="https://github.com/ThursdaysFamous/districtry" target="_blank" rel="noopener">View source on GitHub</a>
      %(byline_begin)s
%(byline_body)s
%(byline_end)s
    </div>
  </div>
</footer>

</body>
</html>
""" % dict(
        mark=mark, title=esc(title), subtitle=esc(subtitle), lede=lede["html"],
        cta=lede["cta"], sections=sections, related=related, app=esc(app_name),
        lookup_begin=marker("GENERATED", "question-lookup", False, "html"),
        lookup_body=preserved["question-lookup"],
        lookup_end=marker("GENERATED", "question-lookup", True, "html"),
        table_begin=marker("GENERATED", "officeholder-table", False, "html"),
        table_body=preserved["officeholder-table"],
        table_end=marker("GENERATED", "officeholder-table", True, "html"),
        byline_begin=marker("ENGINE", "footer-byline", False, "html"),
        byline_body=preserved["footer-byline"],
        byline_end=marker("ENGINE", "footer-byline", True, "html"),
    ))
    return "".join(parts)


MARK_RE = r'(<svg class="districtry-mark".*?</svg>)'


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
        page = head(tag, metros, brand, app_name, page_file, title, desc, og)
        page += shell(app_name, title, subtitle, lede, sections,
                      related_rows(tag, page_file, landing, metros), preserved,
                      themeboot, mark)
        results.append((os.path.join(tag, page_file), path, page, seats))
    return results
MARK = ('<svg class="districtry-mark" viewBox="0 0 96 96" aria-hidden="true">'
        '<g style="mix-blend-mode:multiply"><polygon points="51.5,63.2 12.4,55.7 11.5,18.6 42.7,5.0 72.7,35.3" fill="#6d3fd1" fill-opacity="0.55"></polygon></g>'
        '<g style="mix-blend-mode:multiply"><polygon points="54.1,81.9 34.6,47.9 56.5,19.3 87.5,28.1 83.8,71.0" fill="#1d5fd6" fill-opacity="0.5"></polygon></g>'
        '<g style="mix-blend-mode:multiply"><polygon points="13.7,64.5 27.6,31.2 62.7,37.6 70.3,66.9 33.9,89.0" fill="#b0316e" fill-opacity="0.45"></polygon></g>'
        '<circle cx="42" cy="60" r="17" fill="none" stroke="#17161c" stroke-width="11"></circle>'
        '<line x1="59" y1="16" x2="59" y2="82.5" stroke="#17161c" stroke-width="11"></line></svg>')


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="drift gate: fail rather than write")
    args = ap.parse_args()

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
