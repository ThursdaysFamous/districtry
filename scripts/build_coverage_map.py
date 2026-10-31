#!/usr/bin/env python3
"""Build the root coverage map — the "where it answers today" iframe embedded
in the landing page (scripts/build_landing_page.py).

WHY THIS EXISTS, AND WHY IT DID NOT UNTIL NOW. build_landing_page.py's own
docstring used to rule this out: "it would need Leaflet plus an instance's
own boundary data, and a fleet page that loads one instance's geometry is
telling a lie about the other two." That objection was about ONE instance's
shape standing in for the whole fleet, not about maps in general — so the fix
is not to avoid a map, it is to draw every instance's OWN published outline,
each from the same pre-simplified files its own app already ships
(data/app/metro-outline.json, and data/app/<tag>-state-outline.json where an
instance draws a second, wider tier). Nothing here embeds boundary data: it
only emits the fetch() calls, the same way the design prototype did, so the
browser pulls each file same-origin at view time and a boundary edit needs no
rebuild here.

TWO TIERS, BECAUSE COVERAGE IS NOT ONE THING. Illinois and Wisconsin each
publish statewide layers (county, township, municipality, school district,
ZIP) that answer anywhere in the state, and county-DISPATCHED concept layers
(county-board, judicial-subcircuit, fire-district, ...) that reach only the
counties with a dispatch entry. Illinois's two tiers currently differ in
extent (91 of 102 counties vs. all of Illinois); Wisconsin's happen to
coincide today (all 72 counties carry a county-board entry) but are still two
distinct geometries, because a DIFFERENT county-dispatched concept can lag
behind. Iowa shipped complete across all 99 counties from its first PR, so it
carries one tier only (AREAS below gives it no state_outline). Michigan is one
tier for a different reason worth stating: it has no county-DISPATCHED layer at
all — its commissioner districts come from ONE statewide state-published
compilation covering all 83 counties, so there is no narrower tier that could
ever lag. New York City and San Francisco are city instances, not
county-dispatched at all, and get a point marker at their bbox center rather
than a wash.

TIDIED ON 2026-10-13, BECAUSE THE FLOATING LEGEND STOPPED FITTING. The map was
drawn when a handful of places were live, with a 236px legend floating over its
eastern third. At eleven places that legend hid New York outright and cut North
Carolina to "North"; at thirteen (South Carolina and Tennessee) it covered most
of the Carolinas on a computer and nearly the whole map on a phone, while the
full place names collided wherever small states sit together (Wisconsin into
Michigan, Illinois into Indiana). Adam chose the tidied real map over a tile
grid on 2026-10-13, so the outlines stay and what crowded them goes:
  * NO LEGEND. Its rows repeated the place list the landing page prints under
    the frame, and its colour swatches were all one blue, so they said nothing.
    The landing page now carries the key and one list of every state and DC.
  * TWO-LETTER LABELS, AND ONLY WHERE THEY FIT. Each area is labelled with its
    tag in capitals at the centre of its LARGEST part (so Michigan's sits on the
    lower peninsula, not in the lake), and a label is hidden at any zoom where
    that part is too small on screen to hold it. Small neighbours therefore never
    stack their names, at thirteen places or at fifty.
  * A TOOLTIP CARRIES THE SCOPE. Pointing at an area names it and says how much
    of it is covered, assembled exactly as the legend row used to be.
  * THE NO-LABELS BASEMAP. The basemap's own country and sea names were the only
    other words on the map and they competed with ours. Same CARTO host, same
    key, so the privacy page's recipients do not change.
  * NO GLOW. A blurred halo per area merged into one blob as neighbours joined.

    python3 scripts/build_coverage_map.py            # write coverage-map.html
    python3 scripts/build_coverage_map.py --check    # drift gate; exit 1 on diff
"""

import argparse
import difflib
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(REPO_ROOT, "metros.json")
TOKENS = os.path.join(REPO_ROOT, "districtry", "tokens", "districtry.tokens.css")
FONTFACE = os.path.join(REPO_ROOT, "fonts", "barlow-fontface.css")
OUT = os.path.join(REPO_ROOT, "coverage-map.html")
# The app, for its CARTO key — lifted rather than restated, the same way
# build_landing_page.py lifts the 5c mark, so the key has one home.
APP_SOURCE = os.path.join(REPO_ROOT, "il", "index.html")

# Leaflet pinned to the exact version + SRI the fleet's own apps load (grep
# il/index.html rather than retype it — a version bump there is a version
# bump everywhere, this file included). cdnjs, not unpkg: the fleet's one CDN
# convention, and the one the sandboxed dev environment's vendor_leaflet.sh
# already knows how to mirror for headless testing.
LEAFLET_VERSION = "1.9.4"
LEAFLET_JS_INTEGRITY = "sha512-BwHfrr4c9kmRkLw6iXFdzcdWV/PGkVgiIyIWLLlTSXzWQzxuSg4DiQUCpauz/EWjgk5TYQqX/kvn9pG1NpYfqg=="
# il/index.html inlines leaflet.css rather than linking it, so there is no
# committed hash to copy for the plain <link> this file uses instead — this
# is computed straight off the same cdnjs URL (sha512, base64), the same
# bytes vendor_leaflet.sh mirrors for the sandboxed smoke test.
LEAFLET_CSS_INTEGRITY = "sha512-Zcn6bjR/8RZbLEpLIeOwNtzREBAJnUKESxces60Mpoj+2okopSAcSUIUOseddDm0cxnGQzxIR7vJgsLZbdLE3w=="

# tag -> {outline, state_outline}. state_outline is None for a single-tier
# instance (Iowa: complete across all 99 counties from PR 0, so there is no
# narrower dispatched tier to distinguish from the statewide one. Michigan:
# no county-dispatched layer exists at all, so there is no second tier to draw).
AREAS = {
    "il": {"outline": "il/data/app/metro-outline.json", "state_outline": "il/data/app/il-state-outline.json"},
    "wi": {"outline": "wi/data/app/metro-outline.json", "state_outline": "wi/data/app/wi-state-outline.json"},
    "ia": {"outline": "ia/data/app/metro-outline.json", "state_outline": None},
    "mi": {"outline": "mi/data/app/metro-outline.json", "state_outline": None},
    # Minnesota joined at the 2026-09-30 go-live. ONE tier, like ia and mi: its
    # thirteen layers are the national tier, every one of which answers over the
    # whole state, so there is no inner ring for a solid fill to mean. Its
    # coverage_key carries `outside` alone and no `region`, which is the same
    # fact read from the worksheet.
    "mn": {"outline": "mn/data/app/metro-outline.json", "state_outline": None},
    # Kentucky joined at the 2026-09-30 go-live. ONE tier, like ia, mi and mn:
    # its four layers are the national tier, every one of which answers over the
    # whole state, so there is no inner ring for a solid fill to mean. Its
    # coverage_key carries `outside` alone and no `region`, which is the same
    # fact read from the worksheet.
    "ky": {"outline": "ky/data/app/metro-outline.json", "state_outline": None},
    # Indiana joined at the 2026-10-07 go-live. ONE tier, like ia, mi, mn and
    # ky: its eleven layers are the national tier and every one answers over the
    # whole state, so there is no inner ring for a solid fill to mean. Its
    # coverage_key carries `outside` alone and no `region`.
    "in": {"outline": "in/data/app/metro-outline.json", "state_outline": None},
    # North Carolina joined at the 2026-10-09 go-live. ONE tier, like ia, mi,
    # mn, ky and in: its eleven layers are the national tier and every one
    # answers over the whole state. Its coverage_key carries `outside` alone.
    "nc": {"outline": "nc/data/app/metro-outline.json", "state_outline": None},
    # Oklahoma joined at its go-live. ONE tier, like ia, mi, mn, ky, in and
    # nc: its eleven layers are the national tier and every one answers over
    # the whole state. Its coverage_key carries `outside` alone.
    "ok": {"outline": "ok/data/app/metro-outline.json", "state_outline": None},
    # South Carolina joined at its go-live. ONE tier, like ok and nc: its
    # national-tier layers answer over the whole state and its county council
    # districts tile all 46 counties. Its coverage_key carries `outside` alone.
    "sc": {"outline": "sc/data/app/metro-outline.json", "state_outline": None},
    # Tennessee joined at its go-live. ONE tier, like ok: every layer answers
    # over the whole state, the county commission layer included (its 859
    # districts tile all 95 counties). Its coverage_key carries `outside` alone.
    "tn": {"outline": "tn/data/app/metro-outline.json", "state_outline": None},
    # Arkansas joined at its go-live. ONE tier, like tn: every layer answers
    # over the whole state, the quorum court layer included (its 775
    # districts tile all 75 counties). Its coverage_key carries `outside` alone.
    "ar": {"outline": "ar/data/app/metro-outline.json", "state_outline": None},
    # Mississippi joined at its go-live. ONE tier, like tn and ar: its layers
    # answer over the whole state, except the supervisor district layer, which
    # is drawn only in the counties whose current lines are confirmed and hides
    # in the others, where the County card still names all five supervisors.
    # A county-by-county layer is not a second ring the wash could draw, so
    # the coverage_key carries `outside` alone.
    "ms": {"outline": "ms/data/app/metro-outline.json", "state_outline": None},
    # Louisiana joined at its go-live. ONE tier, like ms: its layers answer
    # over the whole state, except the police jury or council district layer,
    # which is drawn only in the six parishes whose current lines are confirmed
    # and hides in the others, where the Parish card still names every member.
    # A parish-by-parish layer is not a second ring the wash could draw, so the
    # coverage_key carries `outside` alone.
    "la": {"outline": "la/data/app/metro-outline.json", "state_outline": None},
    # Missouri joined at its go-live. It is a TWO-TIER area like Illinois:
    # the lighter wash is the whole state, where the national-tier layers and
    # the County card answer, and the solid fill is the counties whose
    # commission districts are drawn (28 at go-live), each joining the ring as
    # its lines are confirmed. The two are different files, read from the
    # worksheet's coverage_key, which carries a `region`.
    "mo": {"outline": "mo/data/app/metro-outline.json", "state_outline": "mo/data/app/mo-state-outline.json"},
    # Virginia joined at its go-live. ONE tier, like la: every layer answers
    # over the whole state, its 95 counties and 38 independent cities, so the
    # coverage ring IS the state and the coverage_key carries `outside` alone.
    "va": {"outline": "va/data/app/metro-outline.json", "state_outline": None},
    # New York joined at the 2026-09-19 go-live. It is a TWO-TIER area and the
    # two geometries are genuinely different: the dashed wash is the whole
    # state, where the county, municipality, village, school-district,
    # judicial-district and ZIP layers answer, and the solid fill is the five
    # boroughs, which is where the city tier (Council, community districts,
    # NYPD precincts, school zones) reaches. Drawing only one would overstate
    # the city or understate the state.
    "ny": {"outline": "ny/data/app/metro-outline.json", "state_outline": "ny/data/app/ny-state-outline.json"},
}
# tag -> point marker (bbox center — no new hand-typed coordinate, derived
# from the same bbox METRO_EXPLORERS already carries for the sibling-metro
# handoff, so a city's marker moves automatically if its bbox is ever tuned).
CITY_TAGS = ["ca"]

DATA_COLOR = "#1d5fd6"

LIGHT_TOKENS = [
    "paper", "font-body", "font-heading", "muted", "brand-600", "brand-tint",
    "ink", "surface", "border", "border-soft", "radius-card", "faint",
]
DARK_TOKENS = [
    "paper", "muted", "brand-tint", "ink", "surface", "border",
    "border-soft", "faint",
]
DARK_EXTRA = {"brand-600": "brand"}

FALLBACK_FACE = """@font-face {
  font-family: 'Barlow Fallback';
  src: local('Arial');
  ascent-override: 100.00%;
  descent-override: 20.00%;
  line-gap-override: 0.00%;
  size-adjust: 101.66%;
}"""


def fail(msg):
    print("build-coverage-map: FAIL — " + msg, file=sys.stderr)
    sys.exit(1)


def read(path, what):
    try:
        with open(path, encoding="utf-8", newline="") as f:
            return f.read()
    except OSError as e:
        fail("cannot read %s (%s): %s" % (os.path.relpath(path, REPO_ROOT), what, e))


def parse_token_block(css, selector, path):
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


def load_carto_key():
    """The fleet's CARTO Basemaps key, read out of the app rather than restated.

    WHY CARTO AND NOT OSM'S OWN TILE SERVER. The design prototype used
    tile.openstreetmap.org, and shipping that would have put a THIRD PARTY THE
    PRIVACY PAGE DOES NOT DISCLOSE in front of every front-door visitor: that
    page names GitHub Pages, CARTO and cdnjs, and its whole standard is that a
    recipient of your IP is named. CARTO is the basemap every app in the fleet
    already uses, on a key already issued for this domain, so the front door
    reaches nobody the site has not already accounted for. It is also better
    cartography for this job: Positron IS the muted paper ground this page
    wants, and Dark Matter is a REAL dark basemap, which retired a
    `saturate/invert/hue-rotate` filter that was faking one. (OSM's own tile
    usage policy also asks that automated and high-volume users stay off those
    servers, which a page embedded on the site's front door would be.)
    """
    src = read(APP_SOURCE, "the app, for the CARTO basemap key")
    m = re.search(r'var BASE_CARTO_KEY = "([^"]+)"', src)
    if not m:
        fail("the app no longer declares BASE_CARTO_KEY — the coverage map reads "
             "the fleet's basemap key from there so it has one home")
    return m.group(1)


def load_metros():
    try:
        manifest = json.loads(read(MANIFEST, "the fleet manifest"))
    except ValueError as e:
        fail("metros.json is not valid JSON: %s" % e)
    metros = manifest.get("metros")
    if not metros:
        fail("metros.json carries no metros")
    for m in metros:
        for key in ("tag", "landing_name", "url", "scope", "bbox"):
            if not m.get(key):
                fail("metro %r has no %r — the coverage map is generated from "
                     "these fields, so a new metro must carry them" % (m.get("id", "?"), key))
    return metros


def bbox_center(b):
    return ((b["minLat"] + b["maxLat"]) / 2.0, (b["minLng"] + b["maxLng"]) / 2.0)


# Roughly the longitude of the continental US's midpoint — enough to tell a
# west-coast city marker from an east-coast one so its label extends AWAY
# from the map's near edge instead of running off it. A city marker's label
# needs this per-marker judgment call regardless of how many cities the
# fleet ever carries; there is no fact to read it from.
CONUS_MID_LNG = -98.0


def city_label_placement(lng):
    """(className suffix, iconAnchor) so the label text runs away from the
    nearest map edge: right-aligned and anchored leftward of the dot for an
    eastern city, left-aligned and anchored rightward of the dot for a
    western one."""
    if lng > CONUS_MID_LNG:
        return "city-label label-right", [129, 7]
    return "city-label label-left", [-9, 7]


def render_area(m):
    spec = AREAS[m["tag"]]
    outline = os.path.join(REPO_ROOT, spec["outline"])
    if not os.path.isfile(outline):
        fail("%s (area %s) does not exist — has it moved?" % (spec["outline"], m["tag"]))
    state_outline = spec["state_outline"]
    if state_outline:
        full = os.path.join(REPO_ROOT, state_outline)
        if not os.path.isfile(full):
            fail("%s (area %s) does not exist — has it moved?" % (state_outline, m["tag"]))
    return (
        "  { tag: %s, name: %s, url: %s, file: %s, state: %s, scope: %s }"
        % (json.dumps(m["tag"]), json.dumps(m["landing_name"], ensure_ascii=False),
           json.dumps(m["url"]), json.dumps(spec["outline"]),
           json.dumps(state_outline) if state_outline else "null",
           json.dumps(m["scope"], ensure_ascii=False))
    )


def render_city(m):
    lat, lng = bbox_center(m["bbox"])
    cls, anchor = city_label_placement(lng)
    return (
        "  { tag: %s, name: %s, url: %s, lat: %s, lng: %s, scope: %s, cls: %s, anchor: %s }"
        % (json.dumps(m["tag"]), json.dumps(m["landing_name"], ensure_ascii=False),
           json.dumps(m["url"]), json.dumps(round(lat, 4)), json.dumps(round(lng, 4)),
           json.dumps(m["scope"], ensure_ascii=False), json.dumps(cls), json.dumps(anchor))
    )


def build():
    metros = load_metros()
    tokens_css = read(TOKENS, "the design tokens")
    light = parse_token_block(tokens_css, ":root", TOKENS)
    dark = parse_token_block(tokens_css, '[data-theme="dark"]', TOKENS)
    fontface = read(FONTFACE, "the self-hosted font CSS").rstrip("\n")
    if "@font-face" not in fontface:
        fail("fonts/barlow-fontface.css carries no @font-face — regenerate it with "
             "`python3 scripts/build_fonts.py landing > fonts/barlow-fontface.css`")

    unknown = [m["tag"] for m in metros if m["tag"] not in AREAS and m["tag"] not in CITY_TAGS]
    if unknown:
        fail("metro tag(s) %s are in metros.json but not in AREAS or CITY_TAGS above — "
             "a new metro needs a coverage-map entry (an outline pair, or a marker)"
             % ", ".join(unknown))

    areas_js = ",\n".join(render_area(m) for m in metros if m["tag"] in AREAS)
    cities_js = ",\n".join(render_city(m) for m in metros if m["tag"] in CITY_TAGS)

    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<title>districtry — coverage map</title>
<meta name="robots" content="noindex" />
<!-- The tile host is a third origin reached only after Leaflet parses and the
     map builds, so the TCP+TLS handshake is on the critical path for the first
     tile. Same hint the apps carry, for the same reason. -->
<link rel="preconnect" href="https://tiles.basemaps.cartocdn.com" crossorigin />
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/%(lv)s/leaflet.css" integrity="%(css_i)s" crossorigin="" />
<!-- Not `defer`: the inline script below runs immediately after this one and
     calls L.map() directly, so this needs to have already executed by then.
     A small blocking <script> in <head> is a fine trade for a lazy-loaded
     utility iframe — simpler than coordinating two deferred scripts' order. -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/%(lv)s/leaflet.js" integrity="%(js_i)s" crossorigin=""></script>
<!-- GENERATED by scripts/build_coverage_map.py from metros.json + the districtry
     tokens + each instance's own data/app/*outline*.json. Do NOT hand-edit:
     `--check` fails the build. Embedded in the landing page via <iframe>. -->
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
html, body { margin: 0; height: 100%%; background: var(--paper); font-family: var(--font-body); }
#map { position: absolute; inset: 0; background: var(--paper); }
.leaflet-container { font-family: var(--font-body); background: var(--paper); }
/* The attribution takes the theme's own surface rather than a hardcoded white
   wash — on a dark page that literal was a bright strip along the bottom edge,
   the one element that never got the memo. --surface is opaque in both tiers,
   which is what this needs: it sits over map tiles and has to stay legible.
   THE SELECTOR MUST CARRY TWO CLASSES: leaflet.css sets this background on
   `.leaflet-container .leaflet-control-attribution`, so a single-class rule
   here loses on specificity and the white survives with nothing to show for
   the override but a line of CSS that reads as though it worked. */
.leaflet-container .leaflet-control-attribution { font-size: 10px; color: var(--muted); background: var(--surface); }
.leaflet-container .leaflet-control-attribution a { color: var(--brand-600); }
/* Leaflet's zoom buttons are a white box with dark glyphs, hardcoded. On Dark
   Matter that is the brightest thing on the map. The app carries the same
   override for the same reason; `--surface` and `--ink` already flip, so this
   only needs to say that the control uses them. */
.leaflet-bar a, .leaflet-bar a:hover {
  background-color: var(--surface); color: var(--ink); border-bottom-color: var(--border);
}
.leaflet-bar a:hover { background-color: var(--brand-tint); }
.leaflet-touch .leaflet-bar { border-color: var(--border); }
/* NO tile filter here, deliberately. An earlier draft rode OSM's own raster
   and had to fake both themes with saturate/brightness and an invert +
   hue-rotate pass. CARTO's Positron and Dark Matter ARE the two grounds this
   page wants, drawn that way rather than filtered into it — so the light
   basemap is genuinely pale and the dark one is genuinely dark, and the
   coverage wash keeps its true colour on both. They are the NO-LABELS styles
   since 2026-10-13: the basemap's own country and sea names were the only
   other words on the map, and they competed with ours. */
/* One short label per area, the two-letter tag a reader already knows from an
   envelope. The script hides any label whose area is too small on screen to
   hold it, so neighbours never stack their names on top of each other. */
.tag-label {
  font: 700 12px/1 var(--font-heading); letter-spacing: .06em; color: var(--ink);
  text-shadow: 0 0 3px var(--paper), 0 0 3px var(--paper), 0 0 6px var(--paper);
  white-space: nowrap; background: none; border: none; pointer-events: none;
  display: flex; align-items: center; justify-content: center;
}
.tag-label.hidden { visibility: hidden; }
.city-label { font-weight: 600; letter-spacing: 0; }
.label-left { justify-content: flex-start; }
.label-right { justify-content: flex-end; }
/* The tooltip replaces the legend row: the place's name, how much of it is
   covered, and that a click opens it. Theme tokens, so it flips with the page;
   Leaflet's own tooltip is a white box with a pointer, both hardcoded. */
.leaflet-tooltip.place-tip {
  background: var(--surface); color: var(--ink); border: 1px solid var(--border);
  border-radius: 8px; box-shadow: 0 4px 14px rgba(23,22,28,.12); padding: 7px 10px;
  font: 13px/1.35 var(--font-body); white-space: nowrap;
}
.leaflet-tooltip.place-tip::before { display: none; }
.place-tip .nm { display: block; font: 600 15px/1.2 var(--font-heading); }
.place-tip .mt { display: block; color: var(--muted); }
.place-tip .go { display: block; margin-top: 2px; color: var(--brand-600); }
/* Shown only if the outlines cannot be fetched: the place list under the frame
   on the landing page still works, and the reader is told so. */
.map-note {
  position: absolute; z-index: 500; left: 12px; right: 12px; bottom: 22px; margin: 0;
  padding: 10px 12px; background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-card); font-size: 12.5px; line-height: 1.45; color: var(--muted);
}
</style>
</head>
<body>
<!-- No role="img" on the map: it holds Leaflet's own focusable zoom controls,
     and role="img" makes a subtree presentational, so it would hide them from
     assistive tech. The accessible statement of the same fact is the landing
     page's list of every state under this frame — real links, one per place —
     and it is also what a reader is left with if the outlines fail to fetch. -->
<div id="map"></div>
<p class="map-note" hidden>The coverage outlines could not be loaded. The list of places under this map still works.</p>
<script>
var AREAS = [
%(areas_js)s
];
var CITIES = [
%(cities_js)s
];
var DATA = %(data_color)s;
var CARTO_KEY = %(carto_key)s;

if (typeof L === "undefined") {
  document.getElementById("map").outerHTML =
    '<p style="margin:24px;font:14px var(--font-body,sans-serif);color:var(--muted,#666)">' +
    'The coverage map could not load. The list of places under it still works.</p>';
} else {
  /* No zoom buttons in a frame narrower than a small tablet: on a phone the
     frame is about 210px tall and the buttons took a quarter of it, while
     pinching still zooms. */
  var map = L.map("map", {
    zoomControl: window.innerWidth >= 480, scrollWheelZoom: false, attributionControl: true,
    minZoom: 2, maxZoom: 9, zoomSnap: 0.25
  });
  /* The fleet's own basemap, raster tier. The apps upgrade to the MapLibre
     vector build; this page stays on raster on purpose — it is a static
     overview inside a lazy iframe, and a 1 MB GL bundle to draw a few dozen
     polygons at zoom 4 is not a trade worth making. The ATTRIBUTION IS THE
     LICENCE: CARTO's free tier is domain + quota enforced in exchange for
     the visible OSM + CARTO credit, so it is not decoration. */
  function tileUrl(kind) {
    return "https://{s}.basemaps.cartocdn.com/" + kind + "/{z}/{x}/{y}{r}.png?key=" + CARTO_KEY;
  }
  var darkQuery = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;
  function isDark() { return !!(darkQuery && darkQuery.matches); }
  function tileKind() { return isDark() ? "dark_nolabels" : "light_nolabels"; }
  var tiles = L.tileLayer(tileUrl(tileKind()), {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> ' +
      'contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
  }).addTo(map);
  /* The statewide wash is lighter than the inner tier on both grounds, but a
     light-ground opacity all but vanishes on Dark Matter, so it has its own. */
  function washOpacity() { return isDark() ? 0.28 : 0.16; }
  var washes = [];
  /* A reader who flips their system theme with this page open gets the other
     basemap, rather than a pale one on a dark page until they reload. */
  if (darkQuery) {
    var onScheme = function () {
      tiles.setUrl(tileUrl(tileKind()));
      washes.forEach(function (w) { w.setStyle({ fillOpacity: washOpacity() }); });
    };
    if (darkQuery.addEventListener) darkQuery.addEventListener("change", onScheme);
    else if (darkQuery.addListener) darkQuery.addListener(onScheme);
  }
  map.fitBounds([[24.6, -124.6], [49.2, -67.2]], { padding: [6, 6] });
  function open_(url) { window.open(url, "_blank", "noopener"); }

  /* The tooltip is built from DOM nodes and textContent, never a markup
     string: every word in it comes from metros.json. */
  function tip(name, meta) {
    var el = document.createElement("div");
    [["nm", name], ["mt", meta], ["go", "Open the map \u2192"]].forEach(function (part) {
      var s = document.createElement("span");
      s.className = part[0];
      s.textContent = part[1];
      el.appendChild(s);
    });
    return el;
  }

  /* Each label sits at the centre of its area's LARGEST part — Michigan's on
     the lower peninsula, not in the lake between its two halves — and is shown
     only while that part is big enough on screen to hold it. */
  function ringArea(r) {
    var a = 0;
    for (var i = 0, j = r.length - 1; i < r.length; j = i++) a += (r[j][0] + r[i][0]) * (r[j][1] - r[i][1]);
    return Math.abs(a / 2);
  }
  function ringCentre(r) {
    var a = 0, x = 0, y = 0;
    for (var i = 0, j = r.length - 1; i < r.length; j = i++) {
      var f = r[j][0] * r[i][1] - r[i][0] * r[j][1];
      a += f; x += (r[j][0] + r[i][0]) * f; y += (r[j][1] + r[i][1]) * f;
    }
    return [y / (3 * a), x / (3 * a)];
  }
  function largestRing(gj) {
    var best = null, bestArea = 0;
    (gj.features || [gj]).forEach(function (f) {
      var g = f.geometry || f;
      var polys = g.type === "Polygon" ? [g.coordinates] : g.type === "MultiPolygon" ? g.coordinates : [];
      polys.forEach(function (p) {
        var area = ringArea(p[0]);
        if (area > bestArea) { bestArea = area; best = p[0]; }
      });
    });
    return best;
  }
  var labels = [];
  function label(latlng, text, className, iconSize, iconAnchor) {
    var m = L.marker(latlng, {
      interactive: false,
      icon: L.divIcon({ className: className, html: "", iconSize: iconSize, iconAnchor: iconAnchor })
    }).addTo(map);
    m.getElement().textContent = text;
    return m;
  }
  function areaLabel(ring, text) {
    var lats = ring.map(function (p) { return p[1]; }), lngs = ring.map(function (p) { return p[0]; });
    var box = L.latLngBounds([Math.min.apply(null, lats), Math.min.apply(null, lngs)],
                             [Math.max.apply(null, lats), Math.max.apply(null, lngs)]);
    labels.push({ marker: label(ringCentre(ring), text, "tag-label", [40, 14], [20, 7]), box: box });
  }
  function fitLabels() {
    labels.forEach(function (l) {
      var nw = map.latLngToContainerPoint(l.box.getNorthWest());
      var se = map.latLngToContainerPoint(l.box.getSouthEast());
      l.marker.getElement().classList.toggle("hidden", (se.x - nw.x) < 30 || (se.y - nw.y) < 20);
    });
  }
  map.on("zoomend", fitLabels);

  Promise.all(AREAS.map(function (a) {
    return Promise.all([
      fetch(a.file).then(function (r) { return r.json(); }),
      a.state ? fetch(a.state).then(function (r) { return r.json(); }) : Promise.resolve(null)
    ]).then(function (v) { return { a: a, gj: v[0], sgj: v[1] }; });
  }))
    .then(function (loaded) {
      loaded.forEach(function (item) {
        var a = item.a, gj = item.gj, sgj = item.sgj;
        /* Two tiers, because one polygon told a lie: the statewide layers answer
           anywhere in the state, and only the county-dispatched concepts stop at
           the coverage area (see the module docstring for why this differs from
           the "no coverage map" call the landing page used to make). */
        var group = L.featureGroup().addTo(map);
        if (sgj) {
          washes.push(L.geoJSON(sgj, {
            style: { color: DATA, weight: 1, opacity: 0.7, fillColor: DATA, fillOpacity: washOpacity() }
          }).addTo(group));
        }
        L.geoJSON(gj, {
          style: { color: DATA, weight: 1, opacity: 0.9, fillColor: DATA, fillOpacity: 0.42 }
        }).addTo(group);
        /* The "statewide, " prefix marks the lighter wash, and it is PREPENDED
           rather than assumed: a one-tier area gets no prefix. A scope that
           already says statewide must not take it twice — New York's is
           "statewide, 5 boroughs in depth", which read "statewide, statewide,
           5 boroughs in depth" before this test, and the doubling was invisible
           in the generated diff because the prefix is added HERE at runtime
           rather than written into the data above. */
        var scopeSaysStatewide = a.scope.toLowerCase().indexOf("statewide") === 0;
        group.bindTooltip(tip(a.name, (sgj && !scopeSaysStatewide ? "statewide, " : "") + a.scope), {
          sticky: true, className: "place-tip", direction: "top", offset: [0, -8]
        });
        group.on("mouseover", function () { group.setStyle({ weight: 2 }); });
        group.on("mouseout", function () { group.setStyle({ weight: 1 }); });
        group.on("click", function () { open_(a.url); });
        areaLabel(largestRing(sgj || gj), a.tag.toUpperCase());
      });
      CITIES.forEach(function (c) {
        L.circleMarker([c.lat, c.lng], {
          radius: 5.5, color: "#fff", weight: 1.6, fillColor: DATA, fillOpacity: 1
        }).addTo(map)
          .bindTooltip(tip(c.name, c.scope), { className: "place-tip", direction: "top", offset: [0, -6] })
          .on("click", function () { open_(c.url); });
        label([c.lat, c.lng], c.name, "tag-label " + c.cls, [120, 14], c.anchor);
      });
      fitLabels();
    })
    ["catch"](function () {
      document.querySelector(".map-note").hidden = false;
    });
}
</script>
</body>
</html>
""" % {
        "lv": LEAFLET_VERSION,
        "css_i": LEAFLET_CSS_INTEGRITY,
        "js_i": LEAFLET_JS_INTEGRITY,
        "fontface": fontface + "\n" + FALLBACK_FACE,
        "light": token_css(LIGHT_TOKENS, light, ":root"),
        "dark": token_css(DARK_TOKENS, dark, '[data-theme="dark"]', DARK_EXTRA, indent="    "),
        "areas_js": areas_js,
        "cities_js": cities_js,
        "data_color": json.dumps(DATA_COLOR),
        "carto_key": json.dumps(load_carto_key()),
    }


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="verify the committed coverage-map.html matches; exit 1 on drift")
    args = ap.parse_args()

    rendered = build()

    if args.check:
        try:
            with open(OUT, encoding="utf-8", newline="") as f:
                current = f.read()
        except OSError as e:
            fail("cannot read coverage-map.html: %s" % e)
        if current != rendered:
            for dl in list(difflib.unified_diff(
                    current.splitlines(), rendered.splitlines(),
                    fromfile="committed coverage-map.html", tofile="regenerated",
                    lineterm="", n=1))[:40]:
                print("  " + dl, file=sys.stderr)
            fail("coverage-map.html has drifted from metros.json + the districtry tokens. "
                 "Edit the DATA and regenerate; never hand-edit the coverage map.")
        print("build-coverage-map: OK — coverage-map.html matches metros.json (%d place(s))"
              % len(load_metros()))
        return

    with open(OUT, "w", encoding="utf-8", newline="") as f:
        f.write(rendered)
    print("build-coverage-map: wrote coverage-map.html — %d place(s), %d bytes"
          % (len(load_metros()), len(rendered)))


if __name__ == "__main__":
    main()
