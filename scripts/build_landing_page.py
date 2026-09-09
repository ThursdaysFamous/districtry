#!/usr/bin/env python3
"""Build the root landing page — the fleet's front door (R4, docs/DEV_PROCESS_ASSESSMENT.md;
address-first redesign with a coverage map, from the Claude Design handoff
"Districtry landing page alternatives").

WHY THIS EXISTS. "One repo, one site" only pays off if the site has a front
door. R2.3 moved the Illinois app to /il/ and left the root a redirect stub; R3
brought SF and NYC in as folders. This is the page that finally makes the root
mean something: the brand, an address box that opens the right place, a map of
what's covered, and the list of places the fleet answers for.

IT IS GENERATED, AND THAT IS THE POINT. The rebrand assessment's central finding
was that brand identity had become scattered literals — 98 files carrying
`chidistricts`, seven strings locked inside engine fences, a redesign built twice
because index.html could not be parameterised. A hand-written landing page whose
state list is HTML would reproduce that failure on day one of the fix. So every
fact on this page comes from a file that already owns it:

    metros.json                            the fleet list — name, tag, blurb,
                                            scope, url, bbox
    districtry/tokens/districtry.tokens.css the design tokens (light + dark)
    districtry/icons/favicon.svg           the mark, inlined as a data URI
    fonts/barlow-fontface.css              self-hosted Barlow (build_fonts.py landing)

Adding a state to the fleet is a metros.json entry and a regenerate. Restyling
is a token edit and a regenerate. Neither is an edit to this page.

THE FORWARDING GUARD IS NOT OPTIONAL. Before R2.3 the app lived AT the root, and
every share link and embed snippet it handed out was built from the root URL:

    https://chidistricts.com/?utm_source=share&utm_medium=link#point=41.88,-87.63&layers=ward
    <iframe src="https://chidistricts.com/?utm_source=embed&utm_medium=iframe#point=...">

Those are in other people's pages and bookmarks and cannot be recalled. The
redirect stub forwarded them; a landing page that simply replaced it would turn
every one of them into a page about Illinois instead of the map they asked for.
So the root still forwards ANY url carrying app parameters — a #point=/#layers=
permalink, or the share/embed campaign tags — and renders the landing page only
for a bare visit. The guard runs in <head> before the body paints, so a
forwarded visit never flashes this page.

THE COVERAGE MAP EXISTS NOW, AND THE OBJECTION THAT USED TO RULE IT OUT IS
ANSWERED RATHER THAN IGNORED. This docstring used to say no coverage map: "it
would need Leaflet plus an instance's own boundary data, and a fleet page that
loads one instance's geometry is telling a lie about the other two." The
objection was about ONE instance's shape standing in for the whole fleet — so
scripts/build_coverage_map.py draws every instance's OWN published outline
(each already shipped in its own data/app/*.json) rather than picking one.
The <iframe> here just embeds that separately-generated, separately-drift-gated
page; see its own module docstring for the two-tier (statewide vs.
county-dispatched) story it draws.

THE ADDRESS BOX ROUTES FOR REAL. It calls the same Photon endpoint the fleet's
own apps already call for their "did you mean a sibling metro" fallback
(geocodeUnbounded in each instance's ENGINE metro-portal block), tests the
result against each metro's own bbox (the same bbox METRO_EXPLORERS already
carries for that fallback), and sends the reader straight to the covered
instance with the point pre-selected — or says plainly that nowhere covers it
yet, never guessing. This duplicates neither data nor a UI: it is new code
because the root page has no per-instance JS module to call into, but the
provider, the bbox test and the tie-break on an overlap are the same ones
metro-portal already uses.

WHAT IS DELIBERATELY ABSENT. No analytics beyond the fleet's existing GoatCounter
tag (adding a NEW tracker to a new surface is not a build-step decision), and
no per-visitor geolocation (the address box asks for a query the reader typed,
never the browser's location — matching the independence paragraph's promise
that this page does not ask for more than an address).

    python3 scripts/build_landing_page.py            # write index.html
    python3 scripts/build_landing_page.py --check    # drift gate; exit 1 on diff
"""

import argparse
import difflib
import html
import json
import os
import re
import sys
import urllib.parse

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(REPO_ROOT, "metros.json")
TOKENS = os.path.join(REPO_ROOT, "districtry", "tokens", "districtry.tokens.css")
# WHY THE FAVICON IS A FILE AND NOT A data: URI ANY MORE. It was inlined here
# — one fewer request, no flash — and that cost the site its logo in Google
# results. Google's rule is blunt: "Googlebot-Image must be able to crawl the
# favicon file", and there is no file to crawl in a data: URI. districtry.com
# showed the generic globe next to its result, and /favicon.ico 404'd too, so
# the fallback every browser requests unprompted was also missing.
#
# Four declarations, because they answer to different consumers: the SVG for
# modern browsers, a 192px PNG well above Google's 48px recommendation, the ICO
# for the unprompted /favicon.ico request, and apple-touch-icon (which Google
# also accepts) for iOS. Google reads the favicon from the HOME PAGE and applies
# it per HOSTNAME, so this page governs every path under districtry.com — the
# apps keep their own inline mark for their own tabs and it changes nothing for
# search. The URLs must stay put: Google asks that a favicon URL be stable.
FAVICON = os.path.join(REPO_ROOT, "districtry", "icons", "favicon.svg")
# The 5c mark is lifted from the app rather than restated, so the geometry has
# one source. The favicon above is the SIMPLIFIED one-polygon fallback the brand
# spec calls for below 24px — right for a browser tab, wrong for the front door,
# which is why the two are different files doing different jobs.
MARK_SOURCE = os.path.join(REPO_ROOT, "il", "index.html")

# Each instance's worksheet, for the layer count on its pill. A pill that states
# a number must read it from the thing that owns it; a hand-typed count is the
# drift this repo keeps writing generators to avoid.
#
# KEYED BY INSTANCE TAG — the folder, which is the URL, which is the state code
# on the pill. R5 renamed sf/ -> ca/ and nyc/ -> ny/ (the tag is the STATE, not
# the metro: metros.json still calls them 'sf' and 'nyc' by id), and this table
# is the one place that pairs a tag with a file, so it moves with them.
INSTANCE_WORKSHEET = {
    "il": "metro-worksheet.json",
    "ca": "ca/metro-worksheet.json",
    "ny": "ny/metro-worksheet.json",
    "wi": "wi/metro-worksheet.json",
    "ia": "ia/metro-worksheet.json",
    "mi": "mi/metro-worksheet.json",
}
FONTFACE = os.path.join(REPO_ROOT, "fonts", "barlow-fontface.css")
OUT = os.path.join(REPO_ROOT, "index.html")

# The canonical host TODAY. R5 moves this to districtry.com along with
# metros.json's urls; both are data, so that cutover is an edit here plus a
# regenerate, never a rewrite of the page.
CANONICAL = "https://districtry.com/"

# The one external profile that carries the name "districtry" and that this
# project can point at as itself. It goes in the WebSite node's sameAs (below)
# because a coined name has nothing for a search engine to attach it to: the
# root asserted the string and linked it to no identifier anywhere. Only URLs
# that genuinely name this project belong here — the publisher's own GitHub
# account is a different entity and is deliberately not listed.
REPO = "https://github.com/ThursdaysFamous/districtry"

# The rename notice. Data, not markup, so retiring it is deleting a constant
# rather than editing a page — set NOTICE to None when it has served its time.
# It is deliberately plain about what happened and what it means for a reader
# who typed the old name, because that is the only reason they are reading it.
# Presentation: a dismissible toast that auto-fades after NOTICE_SECONDS (the
# Claude Design handoff's default), never persisted across visits — every load
# gets the chance to notice it, exactly like the banner it replaces did.
NOTICE = {
    "heading": "chidistricts.com is now districtry.com",
    "body": ("Same map, same data, same answers — a new name, because it now covers "
             "more than Chicago and more than one state. Illinois lives at "
             "districtry.com/il, and every link below goes straight there."),
}
NOTICE_SECONDS = 15

# The independence line, and it earns its place rather than decorating the page.
# On 2026-08-25 Google Safe Browsing flagged districtry.com under "Deceptive
# pages" — a day-old domain that had just absorbed a mass redirect from an
# established site, asks for a home address, and renders county seals and
# "who represents you", while saying NOWHERE who runs it or that it is
# unofficial. Nothing on the site was deceptive and nothing was compromised
# (every deployed byte matched the repo), but a classifier had no way to tell
# an independent civic reference from an impersonation of one, because the page
# never said. This is the site saying it, above the fold, in its own words.
INDEPENDENCE = (
    "districtry is an independent, unofficial project. It is not a government "
    "service and is not affiliated with, endorsed by, or operated by any "
    "government agency. It asks for an address only to place a point on the "
    "map — there is no account, no sign-in, and it never asks for personal "
    "or financial information."
)

# Where a forwarded visit goes. The Illinois app is what lived at this root
# before R2.3, so it is the only instance whose old links can be in the wild.
FORWARD_TO = "/il/"

# Every US state + DC, so the "not yet" disclosure never needs a hand-typed
# list: it is this set minus whichever metros.json landing_name values are
# themselves a full state (a city instance's landing_name — "New York City",
# "San Francisco" — never matches one, so New York and California correctly
# stay listed even though a city inside each already answers).
US_STATES_AND_DC = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "District of Columbia", "Florida", "Georgia",
    "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky",
    "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
    "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
    "New Hampshire", "New Jersey", "New Mexico", "New York", "North Carolina",
    "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania",
    "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas",
    "Utah", "Vermont", "Virginia", "Washington", "West Virginia", "Wisconsin",
    "Wyoming",
]

# Tokens this page actually sets. Naming them explicitly makes the token file a
# CHECKED dependency: rename one upstream and this build fails by name instead
# of emitting a page with a broken custom property.
LIGHT_TOKENS = [
    "brand-600", "brand-700", "brand-warm", "brand-tint", "brand-border",
    "paper", "surface", "ink", "ink-3", "muted", "faint", "border", "error",
    "font-heading", "font-heading-weight", "font-body",
    "radius-card", "radius-btn", "shadow-card",
]
DARK_TOKENS = [
    "brand-700", "brand-warm", "brand-tint", "brand-border",
    "paper", "surface", "ink", "ink-3", "muted", "faint", "border", "error",
    "shadow-card",
]
# --brand-700 and --brand-warm now EXIST in the token file's dark tier, so the
# dark block takes them by name. They used to be aliased to --brand here, which
# is how this page came to serve #a78bfa where the app serves #c4b0ff for the
# same role on the same brand — the alias was a stand-in for a missing token and
# outlived it.
DARK_EXTRA = {"brand-600": "brand"}


# The metric-matched fallback the body stack names. A real face with no
# download — local('Arial') plus overrides computed with fontTools — so the page
# holds its line metrics while Barlow loads instead of reflowing on swap. It
# lived in the three apps only, while every other surface NAMED it in
# --font-body and did not define it, which is a stack that silently falls
# through to -apple-system. scripts/build_brand_tokens.py --check keeps the
# copies identical. Recompute if the body family or its version changes.
FALLBACK_FACE = """@font-face {
  font-family: 'Barlow Fallback';
  src: local('Arial');
  ascent-override: 100.00%;
  descent-override: 20.00%;
  line-gap-override: 0.00%;
  size-adjust: 101.66%;
}"""


def fail(msg):
    print("build-landing-page: FAIL — " + msg, file=sys.stderr)
    sys.exit(1)


def read(path, what):
    try:
        with open(path, encoding="utf-8", newline="") as f:
            return f.read()
    except OSError as e:
        fail("cannot read %s (%s): %s" % (os.path.relpath(path, REPO_ROOT), what, e))


def parse_token_block(css, selector, path):
    """Return {name: value} for one CSS rule's custom properties."""
    m = re.search(re.escape(selector) + r"\s*\{(.*?)\n\}", css, re.S)
    if not m:
        fail("%s has no %s block" % (os.path.relpath(path, REPO_ROOT), selector))
    return dict(re.findall(r"--([a-z0-9-]+)\s*:\s*([^;]+);", m.group(1)))


def token_css(names, table, where, extra=None, indent="  "):
    out = []
    for n in names:
        if n not in table:
            fail("token --%s is missing from the %s block — renamed upstream?" % (n, where))
        out.append("%s--%s: %s;" % (indent, n, table[n].strip()))
    for alias, src in sorted((extra or {}).items()):
        if src not in table:
            fail("token --%s is missing from the %s block" % (src, where))
        out.append("%s--%s: %s;" % (indent, alias, table[src].strip()))
    return "\n".join(out)


def load_mark():
    """The 5c mark, taken from the app and made theme-aware.

    Two adaptations, both from the brand spec: the polygons MULTIPLY on a light
    ground and SCREEN on a dark one (the app only ever paints light, so it
    hardcodes multiply), and the ring-and-ascender takes currentColor so the
    ink follows the theme instead of staying near-black on a dark page.
    """
    src = read(MARK_SOURCE, "the app, for the 5c mark")
    i = src.find('<svg class="districtry-mark"')
    if i < 0:
        fail("the app no longer carries a districtry-mark SVG to lift")
    svg = src[i:src.index("</svg>", i) + len("</svg>")]
    n = svg.count('style="mix-blend-mode:multiply"')
    if n != 3:
        fail("expected the mark's 3 blended polygons, found %d" % n)
    svg = svg.replace('style="mix-blend-mode:multiply"', 'class="mk-blend"')
    if svg.count('stroke="#17161c"') != 2:
        fail("expected the mark's 2 ink strokes (ring + ascender)")
    svg = svg.replace('stroke="#17161c"', 'stroke="currentColor"')
    return svg.replace('<svg class="districtry-mark"', '<svg class="logo-mark"')


def instance_layer_count(tag):
    rel = INSTANCE_WORKSHEET.get(tag)
    if not rel:
        fail("no worksheet mapped for instance %r — add it to INSTANCE_WORKSHEET "
             "so its pill can state a layer count" % tag)
    try:
        w = json.loads(read(os.path.join(REPO_ROOT, rel), "the %s worksheet" % tag))
    except ValueError as e:
        fail("%s is not valid JSON: %s" % (rel, e))
    n = len(w.get("layers") or [])
    if not n:
        fail("%s lists no layers" % rel)
    return n


def load_metros():
    try:
        manifest = json.loads(read(MANIFEST, "the fleet manifest"))
    except ValueError as e:
        fail("metros.json is not valid JSON: %s" % e)
    metros = manifest.get("metros")
    if not metros:
        fail("metros.json carries no metros")
    for m in metros:
        for key in ("tag", "landing_name", "blurb", "scope", "url", "bbox"):
            if not m.get(key):
                fail("metro %r has no %r — the landing page is generated from "
                     "these fields, so a new metro must carry them"
                     % (m.get("id", "?"), key))
    return metros


def oxford_join(items):
    if len(items) <= 1:
        return "".join(items)
    if len(items) == 2:
        return items[0] + " and " + items[1]
    return ", ".join(items[:-1]) + " and " + items[-1]


def render_notice():
    if not NOTICE:
        return ""
    return (
        '    <aside id="notice" class="notice" role="status" aria-live="polite">\n'
        '      <p id="notice-h" class="notice-h">%s</p>\n'
        '      <p class="notice-b">%s</p>\n'
        '      <button type="button" id="notice-dismiss" aria-label="Dismiss this notice">&#x2715;</button>\n'
        '    </aside>\n'
        % (html.escape(NOTICE["heading"]), html.escape(NOTICE["body"]))
    )


def render_independence():
    return ('    <p class="independence">%s</p>\n' % html.escape(INDEPENDENCE))


def render_pills(metros):
    """One pill per place: name, and the layer count as a quiet trailing number.

    The number is bare on screen because that is the design, and bare is
    meaningless read aloud — "Illinois 39" — so the anchor carries an
    aria-label that says what the number counts. `title` keeps the blurb as a
    sighted hover hint; it is deliberately not the accessible name, since a
    two-line blurb is a poor thing to hear in place of a link's text.
    """
    rows = []
    for m in metros:
        n = instance_layer_count(m["tag"])
        rows.append(
            '        <a class="pill" href="%s" title="%s" aria-label="%s, %d layers">%s'
            '<span class="pill-n">%d</span></a>'
            % (html.escape(m["url"], quote=True),
               html.escape(m["blurb"], quote=True),
               html.escape(m["landing_name"], quote=True), n,
               html.escape(m["landing_name"]),
               n)
        )
    return "\n".join(rows)


DC = "District of Columbia"


def render_not_yet(metros):
    """The uncovered list, and a summary phrase that counts it honestly.

    DC is in the list but is not a state, so it is counted separately rather
    than folded into the number — "47 states and DC", never "48 states and
    DC", which is the off-by-one a hand-typed summary invites.
    """
    covered_states = set(m["landing_name"] for m in metros)
    remaining = [s for s in US_STATES_AND_DC if s not in covered_states]
    n_states = len([s for s in remaining if s != DC])
    summary = "%d states" % n_states
    if DC in remaining:
        summary += " and DC"
    items = "\n".join(
        '        <div>%s</div>' % html.escape(s) for s in remaining
    )
    return summary, items


def _landing_jsonld(metros, title, desc):
    """The root's structured data, built from the same metros list the page renders.

    Every instance page carries a WebSite + Organization graph; the root carried
    none, so the one page naming the whole fleet was the one page search engines
    were told nothing about. The ItemList is the instances in the order a reader
    sees them, so the graph and the visible list cannot disagree.
    """
    items = [
        {
            "@type": "ListItem",
            "position": i + 1,
            "name": m.get("landing_name") or m.get("label"),
            "url": m["url"],
        }
        for i, m in enumerate(metros)
    ]
    graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebSite",
                "@id": CANONICAL + "#website",
                "url": CANONICAL,
                "name": "districtry",
                "description": desc,
                "inLanguage": "en-US",
                "sameAs": [REPO],
                "publisher": {"@id": CANONICAL + "#publisher"},
            },
            {
                "@type": "Organization",
                "@id": CANONICAL + "#publisher",
                "name": "Overberg",
                "url": "https://overberg.co",
            },
            {
                "@type": "ItemList",
                "name": "districtry instances",
                "itemListOrder": "https://schema.org/ItemListUnordered",
                "numberOfItems": len(items),
                "itemListElement": items,
            },
        ],
    }
    return json.dumps(graph, indent=2, ensure_ascii=False)


def render_metros_js(metros):
    """The address box's routing table: tag/name/url/bbox, embedded exactly
    like METRO_EXPLORERS is in each instance — enough for the client to
    replicate the same bbox test each app's own metro-portal handoff already
    runs, with nothing fetched for a point only one instance claims.

    Plus `outline`, the path to that instance's OWN published coverage ring,
    for the points where a rectangle cannot answer. It is emitted only where
    the file is actually in the tree (`<tag>/data/app/metro-outline.json`) —
    discovered, not listed, so a new statewide instance gets it the day it
    ships and the city instances, which publish no such ring, simply keep the
    bbox behaviour. The map in the iframe below already fetches these same
    files, so nothing new is published to make this work."""
    rows = []
    for m in metros:
        b = m["bbox"]
        rel = os.path.join(m["tag"], "data", "app", "metro-outline.json")
        outline = ("\n      outline: %s," % json.dumps(rel.replace(os.sep, "/"))
                   if os.path.isfile(os.path.join(REPO_ROOT, rel)) else "")
        rows.append(
            '    { tag: %s, name: %s, url: %s,%s\n'
            '      bbox: { minLat: %s, maxLat: %s, minLng: %s, maxLng: %s } }'
            % (json.dumps(m["tag"]), json.dumps(m["landing_name"], ensure_ascii=False),
               json.dumps(m["url"]), outline, json.dumps(b["minLat"]),
               json.dumps(b["maxLat"]), json.dumps(b["minLng"]), json.dumps(b["maxLng"]))
        )
    return ",\n".join(rows)


def build():
    metros = load_metros()
    tokens_css = read(TOKENS, "the design tokens")
    light = parse_token_block(tokens_css, ":root", TOKENS)
    dark = parse_token_block(tokens_css, '[data-theme="dark"]', TOKENS)

    favicon = read(FAVICON, "the brand mark").strip()
    if not favicon.startswith("<svg"):
        fail("favicon.svg does not start with <svg — is it still an SVG?")
    favicon_uri = "data:image/svg+xml," + urllib.parse.quote(favicon, safe="")

    fontface = read(FONTFACE, "the self-hosted font CSS").rstrip("\n")
    if "@font-face" not in fontface:
        fail("fonts/barlow-fontface.css carries no @font-face — regenerate it with "
             "`python3 scripts/build_fonts.py landing > fonts/barlow-fontface.css`")

    # The question leads and the brand trails — the composition the instance
    # pages carry (docs/DEV_PROCESS_ASSESSMENT.md, "The SEO surface"). Search
    # Console shows the demand is phrased as a question ("what district am i
    # in"), and a brand nobody is searching for yet cannot earn the click.
    title = "What district am I in? Find your district — districtry"
    desc = ("Enter an address or ZIP — districtry shows every civic district that covers "
            "that point on the map, and the people who hold those seats. Free, no login.")

    live_names = oxford_join([m["landing_name"] for m in metros])
    not_yet_summary, not_yet_items = render_not_yet(metros)

    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>%(title)s</title>
<meta name="description" content="%(desc)s" />
<link rel="canonical" href="%(canonical)s" />
<meta name="theme-color" content="%(brand)s" />
<link rel="icon" href="/favicon.svg" type="image/svg+xml" />
<link rel="icon" href="/favicon-192.png" type="image/png" sizes="192x192" />
<link rel="icon" href="/favicon.ico" sizes="32x32" />
<link rel="apple-touch-icon" href="/apple-touch-icon.png" />
<meta name="robots" content="index, follow" />
<meta property="og:type" content="website" />
<meta property="og:site_name" content="districtry" />
<meta property="og:title" content="%(title)s" />
<meta property="og:description" content="%(desc)s" />
<meta property="og:url" content="%(canonical)s" />
<meta property="og:image" content="%(canonical)sog-image.png" />
<meta property="og:image:width" content="1200" />
<meta property="og:image:height" content="630" />
<meta property="og:image:alt" content="districtry — every district that covers a point, and who represents it." />
<meta property="og:locale" content="en_US" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="%(title)s" />
<meta name="twitter:description" content="%(desc)s" />
<meta name="twitter:image" content="%(canonical)sog-image.png" />
<!-- GoatCounter — cookieless page counts. One site for the whole fleet: every instance
     reports to districtry.goatcounter.com and the PATH tells them apart (/, /il, /ny,
     /ca). This page had no analytics at all until then, which made the fleet's front
     door the one page that could not be counted. -->
<script data-goatcounter="https://districtry.goatcounter.com/count"
        async src="//gc.zgo.at/count.js"></script>
<script type="application/ld+json">
%(jsonld)s
</script>
<!-- GENERATED by scripts/build_landing_page.py from metros.json + the districtry
     tokens. Do NOT hand-edit: `--check` fails the build. Add a state to
     metros.json and regenerate. -->
<script>
/* FORWARD ANY OLD APP LINK, RENDER THE LANDING PAGE FOR EVERYTHING ELSE.

   Before R2.3 the Illinois app served from this root, and every share link and
   embed snippet it produced was built from the root URL — those are in other
   people's pages and bookmarks and cannot be recalled. A landing page that
   simply replaced the redirect stub would answer all of them with a page about
   Illinois instead of the map they asked for. So: a url carrying app
   parameters still forwards, carrying query AND hash exactly as the stub did.

   The two service-worker lines run on EVERY visit, forwarded or not, and stay
   narrow for the reasons R2.3 recorded: unregister only the registration scoped
   to this origin's root (an unfiltered sweep would kill the /il/ app's own
   worker), and delete only the exact legacy cache name (CacheStorage is
   per-ORIGIN, so a prefix sweep would wipe an instance's ~30 MB precache).

   This runs in <head> before the body paints, so a forwarded visit never
   flashes the landing page. */
(function () {
  try {
    if ("serviceWorker" in navigator && navigator.serviceWorker.getRegistrations) {
      navigator.serviceWorker.getRegistrations().then(function (regs) {
        regs.forEach(function (r) {
          if (r.scope === location.origin + "/") { r.unregister(); }
        });
      })["catch"](function () {});
    }
    if (window.caches && caches.delete) { caches.delete("district-explorer-shell-v51"); }
  } catch (e) { /* cleanup must never block a forward */ }

  var hash = location.hash, query = location.search;
  var isPermalink = /(?:^|[#&])(?:point|layers|zoom)=/.test(hash);
  var isTaggedShare = /[?&]utm_source=(?:share|embed)\\b/.test(query);
  if (isPermalink || isTaggedShare) {
    location.replace("%(forward)s" + query + hash);
  }
})();
</script>
<style>
%(fontface)s

:root {
  color-scheme: light dark;
%(light)s
}
@media (prefers-color-scheme: dark) {
  :root {
%(dark)s
  }
}

* { box-sizing: border-box; }
body {
  margin: 0; min-height: 100vh;
  background: var(--paper); color: var(--ink);
  font: 400 16px/1.55 var(--font-body);
  -webkit-font-smoothing: antialiased;
}
.shell { position: relative; min-height: 100vh; }
.wrap { max-width: 940px; margin: 0 auto; padding: 56px 24px 72px; }

/* The rename toast: absolutely positioned against .shell (full viewport
   width), never against .wrap (the centered 940px column) — it sits near the
   top-right of the WINDOW, matching where a reader's eye actually lands, not
   near the top-right of the text measure. */
.notice {
  position: absolute; z-index: 20; top: 18px; right: 24px;
  width: 480px; max-width: calc(100%% - 48px);
  padding: 14px 40px 15px 18px;
  background: var(--brand-tint); border: 1px solid var(--brand-border);
  border-radius: var(--radius-card); box-shadow: 0 6px 22px rgba(23, 22, 28, .16);
  opacity: 1;
}
.notice-h {
  margin: 0 0 5px; font: var(--font-heading-weight) 17px/1.25 var(--font-heading);
  color: var(--ink);
}
.notice-b { margin: 0; font-size: 14.5px; line-height: 1.5; color: var(--ink-3); max-width: 52em; }
.notice #notice-dismiss {
  position: absolute; top: 9px; right: 10px; width: 26px; height: 26px;
  display: flex; align-items: center; justify-content: center; padding: 0;
  background: transparent; border: 1px solid transparent; border-radius: 999px;
  color: var(--muted); font: 400 13px/1 var(--font-body); cursor: pointer;
  transition: color .14s ease, border-color .14s ease, background .14s ease;
}
.notice #notice-dismiss:hover, .notice #notice-dismiss:focus-visible {
  background: var(--surface); border-color: var(--brand-border); color: var(--ink);
}
@keyframes notice-out { from { opacity: 1; } to { opacity: 0; } }
.notice.is-fading { animation: notice-out 900ms ease forwards; }
@media (prefers-reduced-motion: reduce) { .notice.is-fading { animation-duration: 1ms; } }

/* The logo lockup: the 5c mark beside the wordmark, at a size the mark is
   actually drawn for. The brand spec's blend rule is a REAL rule, not
   decoration — the three polygons read as overlapping translucent districts
   only if they multiply on a light ground and screen on a dark one; keep
   multiply on dark and they go muddy and near-black. */
header.mast { display: flex; align-items: center; gap: 14px; }
.logo-mark { width: 64px; height: 64px; flex: 0 0 auto; color: var(--ink); }
.logo-mark .mk-blend { mix-blend-mode: multiply; }
@media (prefers-color-scheme: dark) {
  .logo-mark .mk-blend { mix-blend-mode: screen; }
}
.wordmark {
  font: var(--font-heading-weight) 52px/1 var(--font-heading);
  letter-spacing: .005em; color: var(--ink);
}

h1 {
  font: 400 26px/1.3 var(--font-heading);
  color: var(--ink-3); margin: 22px 0 0; max-width: 34em;
}
.lede { color: var(--muted); margin: 14px 0 0; max-width: 40em; font-size: 15px; }

.search-card {
  margin: 26px 0 0; padding: 20px 22px 22px;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-card); box-shadow: var(--shadow-card);
}
.search-eyebrow {
  display: block; font: var(--font-heading-weight) 13px/1 var(--font-heading);
  letter-spacing: .09em; text-transform: uppercase; color: var(--faint);
  margin-bottom: 11px;
}
.search-row { display: flex; gap: 10px; align-items: stretch; }
.search-input {
  flex: 1 1 auto; min-width: 0; padding: 12px 14px;
  font: 400 15px/1.3 var(--font-body); color: var(--ink);
  background: var(--paper); border: 1px solid var(--border);
  border-radius: var(--radius-btn);
}
.search-input::placeholder { color: var(--faint); }
.search-input:focus-visible {
  outline: 2px solid var(--brand-600); outline-offset: 1px;
  border-color: var(--brand-border);
}
/* THE LABEL COLOUR FLIPS WITH THE THEME, and it is a contrast fix rather than
   a preference. --brand-600 is #6d3fd1 in light (white on it: 6.40:1, passes
   AA) and #a78bfa in dark — white on THAT is 2.72:1, well under the 4.5:1 AA
   floor for 15px text. Dark ink on the same violet is 6.76:1, and on the
   --brand-700 hover (#c4b0ff) 9.64:1. This is the one place on the page where
   a token pair reverses its foreground, so it is stated rather than inherited. */
.search-button {
  flex: 0 0 auto; padding: 0 22px;
  font: var(--font-heading-weight) 15px/1 var(--font-heading); color: #fff;
  background: var(--brand-600); border: 1px solid var(--brand-600);
  border-radius: var(--radius-btn); cursor: pointer; white-space: nowrap;
}
.search-button:hover { background: var(--brand-700); border-color: var(--brand-700); }
.search-button:focus-visible { outline: 2px solid var(--brand-600); outline-offset: 2px; }
.search-button:disabled { opacity: .6; cursor: default; }
@media (prefers-color-scheme: dark) {
  .search-button { color: var(--paper); }
}
.search-help { margin: 12px 0 0; font-size: 13.5px; line-height: 1.5; color: var(--muted); }
.search-status { margin: 10px 0 0; font-size: 13.5px; line-height: 1.4; min-height: 0; }
.search-status.err { color: var(--error); }

h2 {
  font: var(--font-heading-weight) 15px/1 var(--font-heading);
  letter-spacing: .09em; text-transform: uppercase;
  color: var(--faint); margin: 40px 0 12px;
}
.coverage-frame {
  display: block; width: 100%%; height: 430px;
  border: 1px solid var(--border); border-radius: var(--radius-card);
  background: var(--paper);
}
.coverage-caption {
  margin: 11px 0 0; font-size: 13px; line-height: 1.55; color: var(--muted);
  max-width: 52em;
}

.pills { display: flex; flex-wrap: wrap; gap: 8px; }
.pill {
  display: inline-flex; align-items: baseline; gap: 8px; padding: 7px 13px 8px;
  background: var(--surface); border: 1px solid var(--border); border-radius: 999px;
  text-decoration: none; color: var(--ink);
  font: var(--font-heading-weight) 15px/1 var(--font-heading);
}
.pill:hover, .pill:focus-visible { border-color: var(--brand-border); background: var(--brand-tint); }
.pill:focus-visible { outline: 2px solid var(--brand-600); outline-offset: 2px; }
.pill-n { font: 400 12px/1 var(--font-body); color: var(--faint); font-variant-numeric: tabular-nums; }

.not-yet { margin: 14px 0 0; max-width: 52em; }
.not-yet > summary {
  cursor: pointer; font-size: 13px; line-height: 1.55; color: var(--muted);
}
.not-yet > summary:hover, .not-yet > summary:focus-visible { color: var(--ink-3); }
.not-yet-list {
  margin: 10px 0 0; column-count: 3; column-gap: 22px;
  font-size: 12.5px; line-height: 1.9; color: var(--muted);
}

/* Stated plainly and early, never as a warning banner — it is a fact about who
   this is, not an alarm. See INDEPENDENCE for why it is above the fold. */
.independence {
  margin: 18px 0 0; max-width: 52em; font-size: 13.5px; line-height: 1.55;
  color: var(--muted);
}

.does { display: grid; grid-template-columns: repeat(auto-fit, minmax(255px, 1fr)); gap: 22px 26px; }
.does b { display: block; font: var(--font-heading-weight) 17px/1.25 var(--font-heading); margin-bottom: 5px; }
.does p { margin: 0; font-size: 14px; line-height: 1.55; color: var(--ink-3); }

footer { margin-top: 52px; padding-top: 20px; border-top: 1px solid var(--border); font-size: 13.5px; color: var(--muted); }
footer a { color: var(--brand-600); }
footer a:hover { color: var(--brand-700); }
footer p { margin: 0 0 8px; max-width: 46em; }
/* The front door had no links at all — no way to reach the privacy page
   or the source from the page most visitors land on first. */
/* The support line is the one thing in this footer a reader is being ASKED to
   act on, so it does not sit in the flat link row where it reads as a seventh
   equal item. It was exactly that before: one of six links, in an app footer,
   on a page that never mentioned funding at all. */
footer .support {
  margin: 14px 0 0; padding: 12px 14px; max-width: 46em;
  background: var(--brand-tint); border: 1px solid var(--brand-border);
  border-radius: var(--radius-card); color: var(--ink-3);
}
footer .support b { color: var(--ink); }
footer .foot-links { margin-top: 12px; }

@media (max-width: 560px) {
  .wrap { padding: 36px 18px 56px; }
  .wordmark { font-size: 38px; }
  .logo-mark { width: 48px; height: 48px; }
  h1 { font-size: 22px; }
  .search-row { flex-direction: column; }
  .notice { position: static; width: auto; max-width: none; margin: 0 0 26px; }
  .not-yet-list { column-count: 2; }
  /* Taller, not shorter: at this breakpoint the map's legend stops floating
     and takes a strip along the bottom (see build_coverage_map.py), so the
     frame needs the extra room or the map area is what pays for the panel. */
  .coverage-frame { height: 560px; }
}
</style>
</head>
<body>
  <div class="shell">
%(notice)s    <div class="wrap">
    <header class="mast">
      %(mark)s
      <span class="wordmark">districtry</span>
    </header>

    <h1>Every district that covers a point, and who represents it.</h1>
    <p class="lede">%(desc)s</p>

    <div class="search-card">
      <span class="search-eyebrow">Start with an address</span>
      <form id="search-form" class="search-row">
        <input type="text" id="search-input" class="search-input" name="q"
               placeholder="Street address or ZIP" autocomplete="off"
               aria-label="Street address or ZIP" />
        <button type="submit" id="search-button" class="search-button">Show districts</button>
      </form>
      <p class="search-help">districtry opens the map that covers the point. %(live_names)s answer
         today — an address anywhere else says so instead of guessing.</p>
      <p id="search-status" class="search-status" role="status" aria-live="polite"></p>
    </div>

    <h2>Where it answers today</h2>
    <iframe class="coverage-frame" src="coverage-map.html"
            title="Map of the areas districtry covers today"
            loading="lazy"></iframe>
    <p class="coverage-caption">Two tiers, because coverage is not one thing: the pale dashed area
       is where the statewide layers answer — county, township, municipality, school district,
       ZIP — and the solid fill is where the county-level layers reach as well. The map's own
       legend states how much of each place that is; click an area to open its map.</p>

    <h2>Or choose a place</h2>
    <div class="pills">
%(pills)s
    </div>
    <details class="not-yet">
      <summary>Not yet: %(not_yet_summary)s — what nobody covers yet is listed here
        rather than quietly missing.</summary>
      <div class="not-yet-list">
%(not_yet_items)s
      </div>
    </details>

%(independence)s
    <h2>What it does</h2>
    <div class="does">
      <div>
        <b>Every district, not the one you asked for</b>
        <p>Pick a point and it reports every civic boundary that contains it at once —
           legislative, judicial, policing, schools, and the local special districts most
           tools leave out.</p>
      </div>
      <div>
        <b>The people, where they can be verified</b>
        <p>It names who holds each seat when a published roster says so, and links the
           official body when none does. It never guesses an officeholder.</p>
      </div>
      <div>
        <b>It shows its work</b>
        <p>Every layer names the publisher its boundary came from and where its names come
           from. What nobody publishes is listed too, rather than quietly missing.</p>
      </div>
    </div>

    <footer>
      <p>districtry is a public civic reference built from official published
         boundaries and rosters. It is not a legal record of any district line,
         and it never guesses at who holds a seat — where no verifiable roster
         exists, it links the official body instead.</p>
      <p>It is an <b>independent, unofficial project</b> — not a government service, and
         not affiliated with or endorsed by any government agency. Boundary data and
         officeholder names come from the public sources each place names on its sources
         page; seals and logos shown beside a county belong to that county and indicate
         whose district you are looking at, not any endorsement of this site.</p>
      <p>Built and run by <a href="https://overberg.co/" target="_blank" rel="noopener">Adam
         Overberg</a>. The whole thing is open source — every line that produced this page
         is public, the code under
         <a href="https://github.com/ThursdaysFamous/districtry/blob/main/LICENSE"
            target="_blank" rel="noopener">Apache&nbsp;2.0</a> and the data under
         <a href="https://github.com/ThursdaysFamous/districtry/blob/main/LICENSE-DATA.md"
            target="_blank" rel="noopener">ODbL&nbsp;1.0</a>. Fork it for your own state.</p>
      <p>Each place above names its own sources on its sources page.</p>
      <p class="support"><b>This project is unfunded and run at personal cost.</b> If it is useful
         to you, <a href="https://github.com/sponsors/ThursdaysFamous" target="_blank" rel="noopener">sponsoring
         it on GitHub</a> keeps the rosters current — that is where the ongoing work is. Sponsorship
         buys no placement and no influence over any answer here; the
         <a href="sponsorship.html">sponsorship policy</a> says so in detail.</p>
      <p class="foot-links"><a href="privacy.html">Privacy</a> ·
         <a href="sponsorship.html">Sponsorship</a> ·
         <a href="traffic.html">Traffic</a> ·
         <a href="https://overberg.co/why/" target="_blank" rel="noopener">Why this exists</a> ·
         <a href="https://github.com/ThursdaysFamous/districtry" target="_blank" rel="noopener">Source on GitHub</a></p>
    </footer>
    </div>
  </div>
<script>
(function () {
  /* ---------- rename-notice toast: auto-fades, dismissible ---------- */
  var notice = document.getElementById("notice");
  if (notice) {
    var fadeTimer = null, cleanupTimer = null, faded = false;
    function fade() {
      if (faded) return;
      faded = true;
      clearTimeout(fadeTimer);
      clearTimeout(cleanupTimer);
      var done = function () {
        notice.removeEventListener("animationend", done);
        notice.style.display = "none";
      };
      notice.addEventListener("animationend", done);
      notice.classList.add("is-fading");
      // belt and braces: some browsers skip animationend for a 0-duration
      // reduced-motion run, or a tab backgrounded mid-fade.
      cleanupTimer = setTimeout(done, 3000);
    }
    fadeTimer = setTimeout(fade, %(notice_seconds)d * 1000);
    var dismiss = document.getElementById("notice-dismiss");
    if (dismiss) dismiss.addEventListener("click", fade);
    /* The toast is FIRST in the DOM, so its dismiss button is the page's first
       tab stop: a keyboard reader lands there before anything else. Auto-fading
       it out from under them would destroy the focused element and drop focus
       to <body> mid-navigation. While focus is inside, the timer does not run;
       it restarts when focus leaves. A click still fades immediately, because
       that is the reader ASKING for it to go. */
    notice.addEventListener("focusin", function () { clearTimeout(fadeTimer); });
    notice.addEventListener("focusout", function () {
      if (faded) return;
      clearTimeout(fadeTimer);
      fadeTimer = setTimeout(fade, %(notice_seconds)d * 1000);
    });
  }

  /* ---------- address box: geocode, then route to the covered instance ----------
     Same provider (Photon, unbounded) and the same bbox test each instance's
     own metro-portal ENGINE block already runs for its sibling-metro fallback
     — see this file's module docstring. Takes the first Photon result (of up
     to 5, ranked) that actually falls inside a covered bbox, so a bare place
     name ambiguous across states still has a fair shot at landing correctly
     rather than wherever result #1 happened to be. */
  var METROS = [
%(metros_js)s
  ];

  function metrosClaiming(lat, lng) {
    var out = [];
    for (var i = 0; i < METROS.length; i++) {
      var b = METROS[i].bbox;
      if (lat < b.minLat || lat > b.maxLat || lng < b.minLng || lng > b.maxLng) continue;
      out.push(METROS[i]);
    }
    return out;
  }

  /* THE FALLBACK, AND WHY IT IS ONLY A FALLBACK. Nearest bbox CENTRE was the
   * whole of this function until Michigan shipped. It is wrong wherever a
   * rectangle claims ground its instance does not serve, and Lake Michigan
   * makes that ordinary rather than exotic: Michigan's counties are
   * water-inclusive, so its box reaches Wisconsin's longitudes, and
   * Wisconsin's box covers Michigan's entire Upper Peninsula. Measured over 37
   * real places, nearest-centre misroutes 7 — Marquette, Houghton, Ironwood,
   * Iron Mountain and Menominee MI to /wi/, Sister Bay WI to /mi/, Dubuque IA
   * to /wi/. Smallest bbox AREA was tried as a replacement and is NOT better:
   * also 7, just wrong at different places (it fixes Sister Bay and Dubuque,
   * and breaks Rock Island and Escanaba). No rectangle rule can separate
   * states that interlock across a lake. */
  function nearestByCentre(cands) {
    return function (lat, lng) {
      var best = null, bestDist = Infinity;
      for (var i = 0; i < cands.length; i++) {
        var b = cands[i].bbox;
        var dLat = lat - (b.minLat + b.maxLat) / 2, dLng = lng - (b.minLng + b.maxLng) / 2;
        var d = dLat * dLat + dLng * dLng;
        if (d < bestDist) { best = cands[i]; bestDist = d; }
      }
      return best;
    };
  }

  /* Ray casting against one ring, then the same for its holes. The rings are
   * [lng, lat] GeoJSON pairs, which is why x is the longitude here. */
  function inRing(lat, lng, ring) {
    var inside = false;
    for (var i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      var xi = ring[i][0], yi = ring[i][1], xj = ring[j][0], yj = ring[j][1];
      if ((yi > lat) !== (yj > lat) &&
          lng < (xj - xi) * (lat - yi) / ((yj - yi) || 1e-15) + xi) inside = !inside;
    }
    return inside;
  }

  function inOutline(lat, lng, geojson) {
    var geoms = [];
    if (!geojson) return false;
    if (geojson.type === "FeatureCollection") {
      for (var f = 0; f < (geojson.features || []).length; f++) {
        if (geojson.features[f] && geojson.features[f].geometry) geoms.push(geojson.features[f].geometry);
      }
    } else if (geojson.type === "Feature") { if (geojson.geometry) geoms.push(geojson.geometry); }
    else { geoms.push(geojson); }
    for (var g = 0; g < geoms.length; g++) {
      var geom = geoms[g];
      var polys = geom.type === "Polygon" ? [geom.coordinates]
                : geom.type === "MultiPolygon" ? geom.coordinates : [];
      for (var p = 0; p < polys.length; p++) {
        var poly = polys[p];
        if (!poly || !poly.length || !inRing(lat, lng, poly[0])) continue;
        var inHole = false;
        for (var h = 1; h < poly.length; h++) { if (inRing(lat, lng, poly[h])) { inHole = true; break; } }
        if (!inHole) return true;
      }
    }
    return false;
  }

  var outlineCache = {};
  function loadOutline(metro) {
    if (!metro.outline) return Promise.resolve(null);
    if (!outlineCache[metro.tag]) {
      outlineCache[metro.tag] = fetch(metro.outline)
        .then(function (r) { return r.ok ? r.json() : null; })
        ["catch"](function () { return null; });   // an outage must never break routing
    }
    return outlineCache[metro.tag];
  }

  /* Which instance should answer for this point. Resolves to a metro or null.
   *
   * The bbox is kept as the cheap first pass, and for a point only ONE
   * instance's rectangle claims — the overwhelming majority — nothing is
   * fetched and the answer is immediate. Only a genuinely CONTESTED point
   * pays for the real geometry, and it is geometry this fleet already
   * publishes: each instance's own dissolved coverage ring, the same file the
   * coverage map below already loads. Measured over the same 37 places, the
   * ring answers all 37 correctly and claims no point twice.
   *
   * It refines WHICH claimant wins; it never overrules the rectangle to say
   * NOBODY covers a point. These rings are simplified for drawing, so a
   * shoreline address can sit a few metres outside one, and telling a real
   * reader their home is uncovered on that evidence would be worse than the
   * misroute this replaces. No ring containing it, or no ring shipped, falls
   * back to the centre rule above. */
  function resolveMetro(lat, lng) {
    var cands = metrosClaiming(lat, lng);
    if (!cands.length) return Promise.resolve(null);
    if (cands.length === 1) return Promise.resolve(cands[0]);
    var withRing = [];
    for (var i = 0; i < cands.length; i++) { if (cands[i].outline) withRing.push(cands[i]); }
    if (!withRing.length) return Promise.resolve(nearestByCentre(cands)(lat, lng));
    return Promise.all(withRing.map(loadOutline)).then(function (rings) {
      var hits = [];
      for (var i = 0; i < withRing.length; i++) {
        if (rings[i] && inOutline(lat, lng, rings[i])) hits.push(withRing[i]);
      }
      if (hits.length === 1) return hits[0];
      return nearestByCentre(hits.length ? hits : cands)(lat, lng);
    })["catch"](function () { return nearestByCentre(cands)(lat, lng); });
  }

  var form = document.getElementById("search-form");
  var input = document.getElementById("search-input");
  var button = document.getElementById("search-button");
  var status = document.getElementById("search-status");
  var inFlight = null;

  function setStatus(text, isError) {
    status.textContent = text;
    status.className = "search-status" + (isError ? " err" : "");
  }
  function resetButton() {
    button.disabled = false;
    button.textContent = "Show districts";
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var q = input.value.trim();
    if (!q) { setStatus("Type an address or ZIP first.", true); return; }
    if (inFlight) inFlight.abort();
    inFlight = new AbortController();
    button.disabled = true;
    button.textContent = "Searching\\u2026";
    setStatus("Searching\\u2026", false);
    fetch("https://photon.komoot.io/api/?q=" + encodeURIComponent(q) + "&lang=en&limit=5",
      { signal: inFlight.signal, headers: { Accept: "application/json" } })
      .then(function (res) {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then(function (data) {
        var feats = (data && data.features) || [];
        // Still the FIRST result any instance's bbox claims, not result #1 —
        // a bare place name ambiguous across states gets a fair shot. The
        // coarse pass stays synchronous and unchanged; only the winner is then
        // refined against the real rings, so an uncovered address costs no
        // fetch at all.
        var hit = null;
        for (var i = 0; i < feats.length; i++) {
          var c = feats[i] && feats[i].geometry && feats[i].geometry.coordinates;
          if (!c || c.length < 2) continue;
          if (metrosClaiming(c[1], c[0]).length) { hit = { lat: c[1], lng: c[0] }; break; }
        }
        if (!hit) {
          resetButton();
          setStatus(
            feats.length
              ? "That address is outside every place districtry covers today \\u2014 see what's covered below."
              : "No matches \\u2014 try a fuller address, or pick a place below.",
            true
          );
          return;
        }
        return resolveMetro(hit.lat, hit.lng).then(function (metro) {
          if (!metro) { resetButton(); setStatus("That address is outside every place districtry covers today \\u2014 see what's covered below.", true); return; }
          setStatus("Opening " + metro.name + "\\u2026", false);
          window.location.href = metro.url + "#point=" + hit.lat.toFixed(5) + "," + hit.lng.toFixed(5);
        });
      })
      ["catch"](function (err) {
        if (err && err.name === "AbortError") return;
        resetButton();
        setStatus("Search failed \\u2014 try again, or pick a place below.", true);
      });
  });
})();
</script>
</body>
</html>
""" % {
        "title": html.escape(title, quote=True),
        "desc": html.escape(desc, quote=True),
        "jsonld": _landing_jsonld(metros, title, desc),
        "canonical": CANONICAL,
        "forward": FORWARD_TO,
        "brand": light["brand-600"].strip(),
        "favicon": html.escape(favicon_uri, quote=True),
        "fontface": fontface + "\n" + FALLBACK_FACE,
        "light": token_css(LIGHT_TOKENS, light, ":root"),
        "dark": token_css(DARK_TOKENS, dark, '[data-theme="dark"]', DARK_EXTRA,
                          indent="    "),
        "pills": render_pills(metros),
        "mark": load_mark(),
        "notice": render_notice(),
        "independence": render_independence(),
        "live_names": html.escape(live_names),
        "not_yet_summary": html.escape(not_yet_summary),
        "not_yet_items": not_yet_items,
        "metros_js": render_metros_js(metros),
        "notice_seconds": NOTICE_SECONDS,
    }


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="verify the committed index.html matches; exit 1 on drift")
    args = ap.parse_args()

    rendered = build()

    if args.check:
        try:
            with open(OUT, encoding="utf-8", newline="") as f:
                current = f.read()
        except OSError as e:
            fail("cannot read index.html: %s" % e)
        if current != rendered:
            for dl in list(difflib.unified_diff(
                    current.splitlines(), rendered.splitlines(),
                    fromfile="committed index.html", tofile="regenerated",
                    lineterm="", n=1))[:40]:
                print("  " + dl, file=sys.stderr)
            fail("index.html has drifted from metros.json + the districtry tokens. "
                 "Edit the DATA and regenerate; never hand-edit the landing page.")
        print("build-landing-page: OK — index.html matches metros.json (%d place(s)) "
              "and the districtry tokens" % len(load_metros()))
        return

    with open(OUT, "w", encoding="utf-8", newline="") as f:
        f.write(rendered)
    print("build-landing-page: wrote index.html — %d place(s), %d bytes"
          % (len(load_metros()), len(rendered)))


if __name__ == "__main__":
    main()
