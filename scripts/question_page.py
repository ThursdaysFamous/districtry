#!/usr/bin/env python3
"""
The shared shell every generated question page is built from.

WHY IT IS ITS OWN MODULE. build_legislator_pages.py wrote twelve pages and
owned about 250 lines of head, masthead, marker plumbing and footer to do it.
build_concept_pages.py writes four more of exactly that shape, and the
alternative to this module was a second copy of those 250 lines — the decision
build_about_page.py already forced on the root pages when it needed the privacy
page's shell.

WHAT A QUESTION PAGE IS, mechanically: an instance sub-page that carries the
five regions other generators own, and nothing else in this file writes them.

  ENGINE:tokens-brand      compose_app.py
  ENGINE:styles-subpage    compose_app.py
  ENGINE:footer-byline     compose_app.py
  GENERATED:question-lookup   build_question_forms.py
  GENERATED:officeholder-table  build_officeholder_tables.py

A page born here carries all five EMPTY and the other generators fill them on
their own next run, which is what makes every one of those --checks
order-independent. `preserved_from_disk` reads them back on every rebuild, so
the page generator never clobbers what another wrote.

THE HEAD IS READ, NOT RESTATED. The @font-face set, the theme boot script and
the districtry mark come off the instance's own faq.html rather than being
copied here: they are byte-identical across every sub-page an instance carries,
and a copy of a computed font override is exactly the restatement
build_brand_tokens.py exists to stop.

This module writes no file and has no main. It raises PageError; each caller
catches it and prints its own FAIL line, so the message names the script the
reader actually ran.
"""

import html
import json
import os
import re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METROS = os.path.join(REPO_ROOT, "metros.json")
SITE = "https://districtry.com"
AUTHOR = ('{ "@type": "Person", "@id": "https://districtry.com/#author", '
          '"name": "Adam Overberg", "url": "https://overberg.co", '
          '"email": "hello@overberg.co" }')

# Regions a page generator writes EMPTY and never rewrites afterwards. Each is
# owned by another generator; see the module docstring.
PRESERVED = [
    ("ENGINE", "tokens-brand", "css"),
    ("ENGINE", "styles-subpage", "css"),
    ("ENGINE", "footer-byline", "html"),
    ("GENERATED", "question-lookup", "html"),
    ("GENERATED", "officeholder-table", "html"),
]


class PageError(Exception):
    """Something the caller should turn into its own FAIL line."""


def load(path):
    with open(os.path.join(REPO_ROOT, path), encoding="utf-8") as f:
        return json.load(f)


def marker(kind, name, end, style):
    body = "==== %s:%s %s ====" % (kind, "END" if end else "BEGIN", name)
    return "/* %s */" % body if style == "css" else "<!-- %s -->" % body


def preserved_from_disk(path):
    """What the other four generators wrote, keyed by region name.

    A page that has never been written returns empty strings, which is how a
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
    """A block of the shared sub-page head, read from this instance's own
    faq.html rather than restated here.

    Reading a sibling means a new page cannot ship with a stale copy.
    """
    path = os.path.join(REPO_ROOT, tag, "faq.html")
    with open(path, encoding="utf-8") as f:
        text = f.read()
    found = re.search(pattern, text, re.S)
    if not found:
        raise PageError("cannot find the %s in %s/faq.html — the shared sub-page "
                        "head has changed shape and this generator must be "
                        "updated" % (what, tag))
    return found.group(1)


FONTFACE_RE = r"(/\* Self-hosted subset.*?\n\})\n\n?/\* ==== ENGINE:BEGIN tokens-brand"
# The <script> element that carries the theme key. Matched by its CONTENT
# rather than by its opening comment: the comment is worded differently in
# every instance (measured 2026-09-15), so a pattern keyed on it finds the
# block in two instances and fails in four.
THEMEBOOT_RE = r"(<script>(?:(?!</script>).)*districtry-theme(?:(?!</script>).)*</script>)"
MARK_RE = r'(<svg class="districtry-mark".*?</svg>)'


def head(tag, brand, app_name, page_file, title, description, og_desc):
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


def check_layer(worksheet, layer_id, where):
    """A page names the layer id its map link switches on, because that cannot
    be derived from anything else on the page. It IS checkable against the
    instance's own worksheet, and a page naming a layer its app does not
    register is a dead link that still looks right."""
    ids = {l["id"] for l in worksheet["layers"]}
    if layer_id not in ids:
        raise PageError("%s names layer %r, which its worksheet does not register"
                        % (where, layer_id))
