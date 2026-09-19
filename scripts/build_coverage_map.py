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
BRAND_COLOR = "#6d3fd1"

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
        return "label-right", [129, 7]
    return "label-left", [-9, 7]


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
.glow-pane { filter: blur(7px); }
/* NO tile filter here, deliberately. An earlier draft rode OSM's own raster
   and had to fake both themes with saturate/brightness and an invert +
   hue-rotate pass. CARTO's Positron and Dark Matter ARE the two grounds this
   page wants, drawn that way rather than filtered into it — so the light
   basemap is genuinely pale and the dark one is genuinely dark, and the
   coverage wash keeps its true colour on both. */
.place-label {
  font: 600 12.5px/1 var(--font-heading); color: var(--ink);
  text-shadow: 0 0 4px var(--paper), 0 0 4px var(--paper), 0 0 8px var(--paper);
  white-space: nowrap; background: none; border: none;
  display: flex; align-items: center; justify-content: center;
}
.label-left { justify-content: flex-start; }
.label-right { justify-content: flex-end; }
.legend {
  position: absolute; z-index: 500; right: 14px; bottom: 22px;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-card); box-shadow: 0 1px 3px rgba(23,22,28,.06);
  padding: 12px 14px 13px; width: 236px; max-width: calc(100%% - 28px);
}
.legend h3 {
  margin: 0 0 9px; font: 600 11px/1 var(--font-heading);
  letter-spacing: .09em; text-transform: uppercase; color: var(--faint);
}
.legend a {
  display: flex; align-items: baseline; gap: 8px; padding: 3px 5px; margin: 0 -5px;
  border-radius: 5px; text-decoration: none; color: var(--ink);
  transition: background .14s ease;
}
.legend a:hover, .legend a:focus-visible { background: var(--brand-tint); }
.legend .sw { width: 11px; height: 11px; flex: 0 0 auto; border-radius: 2px; position: relative; top: 2px; }
.legend .nm { font: 600 14px/1.2 var(--font-heading); }
.legend .mt { margin-left: auto; font-size: 11.5px; color: var(--muted); font-variant-numeric: tabular-nums; text-align: right; line-height: 1.35; }
.legend .key { margin: 9px 0 0; padding-top: 8px; border-top: 1px solid var(--border-soft); display: flex; flex-direction: column; gap: 5px; }
.legend .key div { display: flex; gap: 7px; font-size: 11px; line-height: 1.35; color: var(--muted); }
.legend .key .sw { top: 1px; }
.legend p { margin: 8px 0 0; padding-top: 8px; border-top: 1px solid var(--border-soft); font-size: 11px; line-height: 1.45; color: var(--muted); }
/* On a phone the floating legend is wider than half the viewport, so it sat
   ON the map and hid whichever markers were behind it — New York's, at the
   default framing. Below 560px it stops floating: the map gives up its bottom
   strip and the legend fills it edge to edge. The landing page gives the
   iframe extra height at the same breakpoint, so the map keeps a usable area
   rather than being squeezed by the panel it just made room for. */
@media (max-width: 560px) {
  #map { inset: 0 0 208px 0; }
  .legend { left: 8px; right: 8px; bottom: 8px; width: auto; max-width: none; }
}
</style>
</head>
<body>
<!-- No role="img" on the map: it holds Leaflet's own focusable zoom controls,
     and role="img" makes a subtree presentational, so it would hide them from
     assistive tech. The legend below is the accessible statement of the same
     fact — real links, one per place — and it is also what a reader is left
     with if the outlines fail to fetch. -->
<div id="map"></div>
<div class="legend">
  <h3>Covered today</h3>
  <div id="legend-rows"></div>
  <div class="key">
    <div><span class="sw" style="background:#1d5fd65c;border:1px solid #1d5fd6"></span><span>County-level layers reach here</span></div>
    <div><span class="sw" style="background:#1d5fd62b;border:1px dashed #1d5fd6"></span><span>Statewide layers, whole state</span></div>
  </div>
</div>
<script>
var AREAS = [
%(areas_js)s
];
var CITIES = [
%(cities_js)s
];
var DATA = %(data_color)s, BRAND = %(brand_color)s;
var CARTO_KEY = %(carto_key)s;

if (typeof L === "undefined") {
  document.getElementById("map").outerHTML =
    '<p style="margin:24px;font:14px var(--font-body,sans-serif);color:var(--muted,#666)">' +
    'The coverage map could not load. The list of places above still works.</p>';
} else {
  var map = L.map("map", {
    zoomControl: true, scrollWheelZoom: false, attributionControl: true,
    minZoom: 3, maxZoom: 9
  });
  /* The fleet's own basemap, raster tier. The apps upgrade to the MapLibre
     vector build; this page stays on raster on purpose — it is a static
     overview inside a lazy iframe, and a 1 MB GL bundle to draw five
     polygons at zoom 4 is not a trade worth making. The ATTRIBUTION IS THE
     LICENCE: CARTO's free tier is domain + quota enforced in exchange for
     the visible OSM + CARTO credit, so it is not decoration. */
  function tileUrl(kind) {
    return "https://{s}.basemaps.cartocdn.com/" + kind + "/{z}/{x}/{y}{r}.png?key=" + CARTO_KEY;
  }
  var darkQuery = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;
  function tileKind() { return darkQuery && darkQuery.matches ? "dark_all" : "light_all"; }
  var tiles = L.tileLayer(tileUrl(tileKind()), {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> ' +
      'contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
  }).addTo(map);
  /* A reader who flips their system theme with this page open gets the other
     basemap, rather than a pale one on a dark page until they reload. */
  if (darkQuery) {
    var onScheme = function () { tiles.setUrl(tileUrl(tileKind())); };
    if (darkQuery.addEventListener) darkQuery.addEventListener("change", onScheme);
    else if (darkQuery.addListener) darkQuery.addListener(onScheme);
  }
  map.fitBounds([[25.4, -123.8], [48.4, -68.4]], { padding: [8, 8] });
  function open_(url) { window.open(url, "_blank", "noopener"); }

  var glowPane = map.createPane("glow");
  glowPane.classList.add("glow-pane");
  glowPane.style.zIndex = 390;

  var rows = document.getElementById("legend-rows");
  function legendRow(color, name, meta, url) {
    var a = document.createElement("a");
    a.href = url;
    a.innerHTML = '<span class="sw" style="background:' + color + '33;border:1px solid ' + color + '"></span>'
      + '<span class="nm"></span><span class="mt"></span>';
    a.querySelector(".nm").textContent = name;
    a.querySelector(".mt").textContent = meta;
    rows.appendChild(a);
    return a;
  }

  function label(latlng, text, className, iconSize, iconAnchor) {
    var m = L.marker(latlng, {
      interactive: false,
      icon: L.divIcon({ className: className, html: "", iconSize: iconSize, iconAnchor: iconAnchor })
    }).addTo(map);
    m.getElement().textContent = text;
  }

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
        L.geoJSON(sgj || gj, { pane: "glow", style: { color: BRAND, weight: 7, opacity: 0.22, fill: false } }).addTo(map);
        if (sgj) {
          L.geoJSON(sgj, {
            style: { color: DATA, weight: 1.2, opacity: 0.85, dashArray: "4 3", fillColor: DATA, fillOpacity: 0.17 }
          }).addTo(map);
        }
        var layer = L.geoJSON(gj, {
          style: { color: DATA, weight: 1.1, opacity: 0.95, fillColor: DATA, fillOpacity: 0.36 }
        }).addTo(map);
        layer.on("mouseover", function () { layer.setStyle({ fillOpacity: 0.46 }); });
        layer.on("mouseout", function () { layer.setStyle({ fillOpacity: 0.36 }); });
        layer.on("click", function () { open_(a.url); });
        var c = L.geoJSON(sgj || gj).getBounds().getCenter();
        label(c, a.name, "place-label", [110, 14], [55, 7]);
        legendRow(DATA, a.name, (sgj ? "statewide, " : "") + a.scope, a.url);
      });
      CITIES.forEach(function (c) {
        L.circleMarker([c.lat, c.lng], {
          radius: 5.5, color: "#fff", weight: 1.6, fillColor: DATA, fillOpacity: 1
        }).addTo(map).on("click", function () { open_(c.url); });
        label([c.lat, c.lng], c.name, "place-label " + c.cls, [120, 14], c.anchor);
        legendRow(DATA, c.name, c.scope, c.url);
      });
    })
    ["catch"](function () {
      var note = document.createElement("p");
      note.textContent = "The coverage outlines could not be loaded. The list of places above still works.";
      document.querySelector(".legend").appendChild(note);
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
        "brand_color": json.dumps(BRAND_COLOR),
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
