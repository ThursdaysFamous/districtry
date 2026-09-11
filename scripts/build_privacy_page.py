#!/usr/bin/env python3
"""Build the fleet's privacy page — /privacy.html, one page for every app here.

WHY THIS IS ONE PAGE AND NOT THREE. The privacy page shipped at
`il/privacy.html`, describing the Illinois app, on a site that serves three.
NYC and SF had no privacy page at all, and the front door linked Illinois's —
so a reader on /ny/ was either told nothing or told about a different app. One
page at the root is what the reader actually needs: it is the same project, the
same operator, and the same absence of a back end everywhere.

WHY IT IS GENERATED, AND MEASURED FROM THE APPS THEMSELVES. A privacy page is a
set of factual claims about what code does. This one is assembled by READING the
shipped pages — not the worksheets, and not a hand-kept list — because the
worksheets are not the truth here: `ny/` and `ca/` carry EMPTY `brand.analytics`
blocks while their shipped HTML runs GoatCounter, and NYC's runs Google
Analytics as well. A generator trusting the worksheet would have published that
those two apps have no analytics. So every per-app fact below comes from a regex
over the file a reader is actually served.

That also settles the question the old page raised and could not answer for a
fleet: it claimed "some large statewide layers ask the server about your exact
selected point", which is TRUE of Illinois and FALSE of the other two — five
call sites against none. Copying the page across would have shipped a false
confession twice; dropping the sentence would have hidden a true one once.

TWO KINDS OF CLAIM, AND THE BUILD TREATS THEM DIFFERENTLY:

  * FLEET claims — asserted identical across every app, and GATED. The analytics
    event vocabulary and the two-decimal coordinate rounding are engine code, so
    the page states them once; if one app ever diverges, this build FAILS rather
    than publishing a sentence that is true of two apps out of three.
  * PER-APP facts — analytics, browser storage, address search, whether the app
    sends a point to a server — rendered as a table with a row per app, because
    they genuinely differ and a reader deserves to know which one they are on.

    python3 scripts/build_privacy_page.py            # write privacy.html
    python3 scripts/build_privacy_page.py --check    # drift gate; exit 1 on diff
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
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# The token file, the mark and the self-hosted font CSS are the LANDING page's
# declared dependencies, and its helpers already parse them with by-name checks
# that fail on an upstream rename. Importing them keeps one parser for one file;
# a failure in any of the three therefore surfaces under `build-landing-page:`,
# which is the module that owns those files rather than a mislabelled error.
from build_landing_page import (  # noqa: E402
    FALLBACK_FACE, FAVICON, FONTFACE, MANIFEST, TOKENS,
    load_mark, parse_token_block, read, token_css,
)

OUT = os.path.join(REPO_ROOT, "privacy.html")
# Written by scripts/probe_point_transmission.mjs — the ONE fact on this page
# that cannot be read off a file, because it depends on which layers a
# registration factory was called for and on entries a closure holds.
POINT_TRANSMISSION = os.path.join(REPO_ROOT, "point-transmission.json")
CANONICAL = "https://districtry.com/privacy.html"
SITE = "https://districtry.com/"
UPDATED = "24 August 2026"
CONTACT = "adam@overberg.co"
REPO_URL = "https://github.com/ThursdaysFamous/districtry"

LIGHT_TOKENS = [
    "brand-600", "brand-700", "brand-warm", "brand-tint", "brand-border",
    "paper", "surface", "surface-2", "ink", "ink-2", "ink-3", "muted", "faint",
    "border", "border-soft",
    "font-heading", "font-heading-weight", "font-body",
    "radius-card", "shadow-card",
]
DARK_TOKENS = [
    "brand-700", "brand-warm", "brand-tint", "brand-chip", "brand-border",
    "paper", "surface", "surface-2", "ink", "ink-2", "ink-3", "muted", "faint",
    "border", "border-soft", "shadow-card",
]
# --brand-700 and --brand-warm now EXIST in the token file's dark tier, so the
# dark block takes them by name. They used to be aliased to --brand here, which
# is how this page came to serve #a78bfa where the app serves #c4b0ff for the
# same role on the same brand — the alias was a stand-in for a missing token and
# outlived it.
DARK_EXTRA = {"brand-600": "brand"}

# The front door is measured too, and its row is not filler. It used to be the
# one surface here that contacted nobody and stored nothing; since the
# address-first redesign it has a search box of its own, so it now sends a typed
# address to the same geocoder the apps use, and the table says so. That is
# exactly why the row is measured rather than asserted — the claim changed
# because the page changed, and nobody had to remember to come and edit it.
FRONT_DOOR = {"file": "index.html", "name": "The front door", "url": "/", "tag": None}

# Third parties every app reaches, with the policy that governs each. Kept here
# rather than scraped, because a host name is not a policy URL — but the
# PRESENCE of each is measured below, so a fleet that stops using one fails the
# build instead of going on naming it.
# The last slot is the KEY that decides which surfaces the row names, and it is
# measured rather than written. These rows used to end in a flat "Every app.",
# which was true while only the apps drew a map — and stopped being true the day
# the front door embedded a coverage map, silently, on a page whose whole job is
# to say who receives what. `None` means every surface (hosting reaches all of
# them); otherwise it is the measured flag a surface must carry to be named.
COMMON_RECIPIENTS = [
    ("GitHub Pages", "hosting",
     "https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement",
     "The ordinary web-server request for each file — your IP address, browser, and the "
     "page you asked for. GitHub, not this project, keeps those logs.",
     "Every visit.", None),
    ("CARTO", "basemap tiles", "https://carto.com/privacy/",
     "The map tiles you request — which, taken together, describe the area you are "
     "looking at and how far you zoomed in.",
     "Whenever the map draws or moves.", "tiles"),
    ("Cloudflare (cdnjs)", "mapping library", "https://www.cloudflare.com/privacypolicy/",
     "A request for one JavaScript file, Leaflet 1.9.4, pinned by hash.",
     "Every visit to a map.", "cdn"),
]

# Geocoders, keyed by the host the measurement finds. What a geocoder receives is
# the most sensitive flow on the page — it is the text you type — so each is
# named individually rather than pooled into "address search".
# The "what" strings say "as you type OR when you press the button" rather than
# "as you type", because the two kinds of surface differ and the narrower claim
# would be wrong for one of them: the apps' boxes are type-ahead and send on
# each keystroke, while the front door's sends only on submit. Over-stating what
# leaves a browser is the safe direction to be wrong in, and it is still wrong.
GEOCODERS = {
    "photon.komoot.io": (
        "Photon / Komoot", "address search", "https://www.komoot.com/privacy",
        "<strong>The text you type into the search box</strong> — sent as you type on the "
        "apps' type-ahead boxes, and only when you press the button on the front door."),
    "nominatim.openstreetmap.org": (
        "Nominatim / OpenStreetMap", "address search, office pins",
        "https://osmfoundation.org/wiki/Privacy_Policy",
        "The address you searched, when the bounded fallback runs. It also receives "
        "<em>public office addresses from the datasets</em> — a clerk's office, a school "
        "— to place their map pins; that is data about buildings, not about you."),
    "geosearch.planninglabs.nyc": (
        "GeoSearch / NYC Planning", "address search",
        "https://www.nyc.gov/home/privacy-policy.page",
        "<strong>The text you type into the search box</strong>, sent as you type so "
        "suggestions can appear."),
}

# FLEET CLAIMS — stated once on the page, and required to be identical. The
# tuple is what the measurement must return for EVERY app that has a map.
# `metro-portal/` (the sibling-metro CARD was shown) left the vocabulary on
# 2026-08-25 when the card did: the handoff is a silent redirect now, so the
# only portal event an app can send is the departure itself.
EXPECTED_EVENTS = ["address-search", "geolocate", "geolocate-success", "layer/",
                   "metro-portal-go/", "select", "share-native",
                   "share-open"]
EXPECTED_COORD_EVENTS = ["geolocate-success", "select"]
COORD_DECIMALS = 2


def fail(msg):
    print("build-privacy-page: FAIL — " + msg, file=sys.stderr)
    sys.exit(1)


def resolve_key(src, token):
    """The literal behind a storage key, whether inline or held in a var."""
    if token[0] in "\"'":
        return token[1:-1]
    m = re.search(r"\b" + re.escape(token) + r'\s*=\s*"([^"]+)"', src)
    if not m:
        fail("storage key %r is not a plain string constant — this page has to "
             "print the exact key a reader would look for in their browser, so "
             "resolve it here or make it a literal" % token)
    return m.group(1)


def embedded_sources(rel, src):
    """The same-origin pages this one EMBEDS, read so their third parties count
    as this surface's.

    A reader on a page with an <iframe> loads whatever that frame loads —
    their IP reaches its hosts on the same visit, without a click. Measuring
    only the outer document would have let the front door's coverage map bring
    in a basemap host this page never named. Relative srcs only: an off-site
    frame is a different question, and nothing here has one.
    """
    out = []
    base = os.path.dirname(os.path.join(REPO_ROOT, rel))
    for m in re.finditer(r'<iframe[^>]*\ssrc="([^":?#]+\.html)"', src):
        path = os.path.normpath(os.path.join(base, m.group(1)))
        if os.path.isfile(path):
            out.append(read(path, "a page embedded by %s" % rel))
        else:
            fail("%s embeds %s, which does not exist — this page measures what a "
                 "reader's browser actually loads" % (rel, m.group(1)))
    return out


def measure(rel, name, url, tag):
    """Everything this page claims about one app, read off the file it serves."""
    src = read(os.path.join(REPO_ROOT, rel), "the %s app" % name)
    # Whatever it embeds is loaded by the same visit, so it is measured with it.
    # (Appended AFTER the storage/analytics regexes' subject for a reason: those
    # want the outer document's own keys. Only the third-party host checks below
    # read `src_all`.)
    src_all = "\n".join([src] + embedded_sources(rel, src))
    app = {"file": rel, "name": name, "url": url, "tag": tag}

    m = re.search(r"gtag/js\?id=(G-[A-Z0-9]+)", src)
    if m:
        gate = re.search(r"location\.hostname\s*!==\s*'([^']+)'", src)
        if not gate:
            fail("%s loads Google Analytics with no hostname gate — the page says "
                 "GA runs on the live host only, and that would stop being true"
                 % rel)
        app["ga"] = {"id": m.group(1), "host": gate.group(1)}
    else:
        app["ga"] = None

    m = re.search(r'data-goatcounter="(https://([a-z0-9-]+)\.goatcounter\.com/count)"', src)
    app["goatcounter"] = {"url": m.group(1), "site": m.group(2)} if m else None

    storage = {}
    for store in ("sessionStorage", "localStorage"):
        found = set()
        for mm in re.finditer(
                store + r"\.(?:get|set|remove)Item\(\s*([A-Za-z_$][\w$]*|\"[^\"]*\"|'[^']*')",
                src):
            found.add(resolve_key(src, mm.group(1)))
        storage[store] = sorted(found)
    app["storage"] = storage

    app["geocoders"] = [h for h in GEOCODERS if h in src_all]
    # WHAT has_map GATES: the fleet-wide parity claims (identical analytics
    # vocabulary, CARTO tiles, cdnjs), which are claims about the map APPS.
    # It was `bool(app["geocoders"])` — a proxy that held only while the front
    # door had no search box of its own. The address-first redesign gave it
    # one, and the proxy promptly classified the front door as an app and
    # failed the build for not sending the apps' analytics events, which it
    # has never sent and should not. The tag is the real question being asked:
    # a tagged surface is an instance, an untagged one is the root.
    app["has_map"] = tag is not None
    # The HOST, not a subdomain-prefixed form of it. This was
    # `[a-z]\.basemaps\.cartocdn\.com`, which happened to work only because the
    # apps carry `tiles.basemaps…` preconnect hints — the tile URL ITSELF is a
    # Leaflet template, `{s}.basemaps…`, whose character before the dot is `}`.
    # A page that requested CARTO tiles without also preconnecting them measured
    # as requesting no tiles at all.
    app["tiles"] = "basemaps.cartocdn.com" in src_all
    app["cdn"] = "cdnjs.cloudflare.com" in src_all

    # A layer that asks a government server about the SELECTED POINT rather than
    # downloading the layer and testing in the browser.
    #
    # THIS IS NOT COUNTED HERE, AND THAT IS THE FIX OF 2026-09-05. It used to be
    # `loadArcGISPointGeoJSON(` call sites, adjusted for the one wrapper that
    # shares a call site across layers, and it published 10 for Illinois against
    # a true 19 and "None." for New York City against a true 4.
    #
    # A REGEX CANNOT BE RIGHT, for two reasons that were measured rather than
    # assumed. A REGISTRATION FACTORY serves as many layers as it is CALLED from
    # one source occurrence, so counting occurrences is wrong in both directions.
    # And `registerCountyLayer` CLOSES OVER its entries, so the spec it registers
    # never references them and not even a full walk of the live module graph
    # reaches Illinois's `ward` or `county-board` — both of which do send.
    #
    # AND NEITHER CAN A STRUCTURAL READ, which is the correction this comment
    # carries. The first version of that browser probe counted layers whose
    # loader CARRIED an `.atPoint` hook, and that overcounts: the hook is invoked
    # in exactly ONE place in every instance, inside `queryFeatureAt`, and a
    # layer whose query does not route through it never fires the hook it holds.
    # `registerNearestPointLayer.query` calls `opts.loader()` directly, and
    # several NYC and SF layers call their load function directly, so they carry
    # the Socrata hook and send nothing. Counting carriage published il 20, ny 9
    # and ca 3 against a true 19, 4 and 0 — and on this page an OVERCOUNT is a
    # false statement exactly as an undercount is: it has an app confessing to a
    # transmission it does not make. San Francisco's original "None." was right.
    #
    # So the number is MEASURED IN A BROWSER by
    # `scripts/probe_point_transmission.mjs`, which boots each app, REPLACES
    # every `.atPoint` with a recorder, switches on every layer, selects points
    # inside the instance's own coverage and counts the hooks that FIRE. This
    # generator must stay stdlib-only — its CI step has no browser — so it READS
    # that probe's artifact and re-derives a FINGERPRINT of each app to prove the
    # artifact still describes it (see fingerprint() and
    # gate_point_transmission()).
    app["fingerprint"] = fingerprint(src)

    app["events"] = sorted({mm.group(1) for mm in
                            re.finditer(r"trackEvent\(\s*[\"']([^\"']+)[\"']", src)})
    app["coord_events"] = sorted({mm.group(1) for mm in re.finditer(
        r"trackEvent\(\s*[\"']([^\"']+)[\"']\s*,\s*\w+\.toFixed\((\d)\)", src)})
    app["coord_decimals"] = sorted({int(mm.group(1)) for mm in re.finditer(
        r"trackEvent\(\s*[\"'][^\"']+[\"']\s*,\s*\w+\.toFixed\((\d)\)", src)})
    return app


def fingerprint(src):
    """The two things about an app that move whenever its point-sending set can.

    Not a count of anything published — a CHECKSUM the browser probe and this
    generator can both compute, so a stdlib CI step can tell whether the probe's
    artifact still describes the app it was measured from.

      * every `<name>.atPoint = function` site, which is where the hook that
        sends the point is attached; and
      * every registered layer id, taken from the generated LAYER_AREA_RANK in
        the app file itself. That moves when a layer is added, removed or
        renamed INCLUDING one registered through a factory whose call site never
        changes — which is the case a call-site count cannot see.

    WHAT IT DOES NOT COVER, stated rather than implied. Two things move the true
    count while leaving both halves of this fingerprint identical: swapping an
    existing layer's loader for another EXISTING loader that differs only in
    whether it carries `.atPoint`, and REROUTING A LAYER'S QUERY into or out of
    `queryFeatureAt`, which is the only place the hook is ever invoked — a layer
    can hold a hook for years and start or stop firing it with no change to any
    site name or layer id. Nothing short of booting the app can see either, so
    the browser probe's own `--check` (which does boot it, in CI) is the gate for
    both and this is the tripwire for everything else.
    """
    sites = sorted(m.group(1) for m in re.finditer(r"(\w+)\.atPoint\s*=\s*function", src))
    block = re.search(r"var LAYER_AREA_RANK = \[([\s\S]*?)\n\s*\];", src)
    ids = sorted(m.group(1) for m in re.finditer(r'"([^"]+)"', block.group(1))) if block else []
    return {"atpoint_sites": sites, "layer_ids": ids}


def gate_point_transmission(apps):
    """Attach each app's measured point-sending count, or refuse to publish.

    The front door has no tag and no map, and is absent from the artifact by
    construction; it publishes "None." and that is measured too, since a surface
    with no LAYER_AREA_RANK has no layer that could send anything.
    """
    try:
        probe = json.loads(read(POINT_TRANSMISSION, "the point-transmission probe"))
    except ValueError as e:
        fail("point-transmission.json is not valid JSON: %s. Regenerate it with "
             "`node scripts/probe_point_transmission.mjs`" % e)
    measured = probe.get("apps") or {}
    for a in apps:
        if a["tag"] is None:
            a["point_query_layers"] = 0
            continue
        got = measured.get(a["tag"])
        if got is None:
            fail("%s is in metros.json but not in point-transmission.json — this "
                 "page would publish nothing about whether it sends your selected "
                 "point. Run `node scripts/probe_point_transmission.mjs`"
                 % a["file"])
        for key in ("atpoint_sites", "layer_ids"):
            if got.get(key) != a["fingerprint"][key]:
                fail("%s has changed since the point-transmission probe last ran: "
                     "%s is now %s, measured as %s. What it sends about your "
                     "selected point may have changed with it, and this page is "
                     "not going to guess. Run "
                     "`node scripts/probe_point_transmission.mjs`, then rebuild "
                     "this page."
                     % (a["file"], key, a["fingerprint"][key], got.get(key)))
        # The probe records WHICH layers too; nothing renders them, so nothing
        # carries them here. Michigan's go-live shipped a false privacy claim
        # off a helper that was never called — in this module above all others,
        # dead code is not free.
        a["point_query_layers"] = got["layers_sending_point"]


def gate_fleet_claims(apps):
    """Refuse to state as fleet-wide anything one app does differently."""
    maps = [a for a in apps if a["has_map"]]
    if not maps:
        fail("no app measured as carrying a map — the measurement is broken")
    for a in maps:
        if a["events"] != EXPECTED_EVENTS:
            fail("%s sends analytics events %s, not the fleet set %s. The page "
                 "states the event list ONCE as a shared fact; either restore "
                 "parity or move the list into the per-app table."
                 % (a["file"], a["events"], EXPECTED_EVENTS))
        if a["coord_events"] != EXPECTED_COORD_EVENTS:
            fail("%s attaches coordinates to events %s, not %s — the page names "
                 "exactly which two events carry a location"
                 % (a["file"], a["coord_events"], EXPECTED_COORD_EVENTS))
        if a["coord_decimals"] != [COORD_DECIMALS]:
            fail("%s rounds analytics coordinates to %s decimal place(s), not %d. "
                 "The rounding IS the privacy claim — never widen it silently"
                 % (a["file"], a["coord_decimals"], COORD_DECIMALS))
        if not a["tiles"] or not a["cdn"]:
            fail("%s no longer requests %s — the 'who receives what' table names "
                 "it for every app" % (a["file"],
                                       "CARTO tiles" if not a["tiles"] else "cdnjs"))


def load_apps():
    try:
        manifest = json.loads(read(MANIFEST, "the fleet manifest"))
    except ValueError as e:
        fail("metros.json is not valid JSON: %s" % e)
    apps = [measure(FRONT_DOOR["file"], FRONT_DOOR["name"], FRONT_DOOR["url"], None)]
    for m in manifest.get("metros") or []:
        tag = m.get("tag")
        name = m.get("landing_name") or m.get("label")
        if not tag or not name:
            fail("metro %r has no tag/landing_name — this page names each app by "
                 "the same fields the front door does" % m.get("id", "?"))
        apps.append(measure("%s/index.html" % tag, name, "/%s/" % tag, tag))
    return apps


def esc(s):
    return html.escape(s, quote=True)


def joined(names):
    """'a', 'a and b', 'a, b and c' — the page reads as prose, not as a list."""
    names = list(names)
    if len(names) <= 2:
        return " and ".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


def code(s):
    return '<code class="k">%s</code>' % esc(s)


def render_app_rows(apps):
    rows = []
    for a in apps:
        if a["ga"]:
            ga = "Google Analytics %s<small>live host only (%s), never in an embed</small>" % (
                code(a["ga"]["id"]), code(a["ga"]["host"]))
        else:
            ga = "<em>None.</em>"
        gc = (code(a["goatcounter"]["url"]) if a["goatcounter"] else "<em>None.</em>")
        stored = []
        for label, store in (("session", "sessionStorage"), ("kept", "localStorage")):
            for k in a["storage"][store]:
                stored.append("%s<small>%s</small>" % (code(k), label))
        search = ", ".join(GEOCODERS[h][0] for h in a["geocoders"]) or "<em>No search box.</em>"
        point = ("%d layer%s" % (a["point_query_layers"], "" if a["point_query_layers"] == 1 else "s")
                 if a["point_query_layers"] else "<em>None.</em>")
        rows.append(
            "          <tr>\n"
            '            <th scope="row"><a href="%(url)s">%(name)s</a><small>%(url)s</small></th>\n'
            "            <td>%(ga)s</td>\n"
            "            <td>%(gc)s</td>\n"
            "            <td>%(stored)s</td>\n"
            "            <td>%(search)s</td>\n"
            "            <td>%(point)s</td>\n"
            "          </tr>" % {
                "url": esc(a["url"]), "name": esc(a["name"]), "ga": ga, "gc": gc,
                "stored": " ".join(stored) or "<em>Nothing.</em>",
                "search": search, "point": point})
    return "\n".join(rows)


def render_recipient_rows(apps):
    rows = []
    for label, sub, policy, what, when, key in COMMON_RECIPIENTS:
        users = apps if key is None else [a for a in apps if a[key]]
        if not users:
            fail("no surface requests %s any more — the recipients table names it, "
                 "so either the fleet changed or the measurement is broken" % label)
        rows.append(recipient_row(label, sub, policy, what, when,
                                  ", ".join(a["name"] for a in users) + "."))
    for host in sorted({h for a in apps for h in a["geocoders"]}):
        label, sub, policy, what = GEOCODERS[host]
        users = [a["name"] for a in apps if host in a["geocoders"]]
        rows.append(recipient_row(label, sub, policy, what,
                                  "Only while you are searching for an address, or when a "
                                  "card places an office pin.",
                                  ", ".join(users) + "."))
    rows.append(recipient_row(
        "Public GIS services", "the district data itself", None,
        "Requests for boundary and roster data from government servers — the U.S. Census "
        "TIGERweb, ArcGIS services run by cities, counties and states, municipal open-data "
        "portals, and the USGS. Mostly these download a whole layer and the "
        "&#34;which district contains this point&#34; test then runs "
        "<strong>inside your browser</strong>. Where an app is marked in the table above as "
        "sending a point, that layer instead asks the server about "
        "<strong>your exact selected point</strong> so one district can answer immediately "
        "while the full layer downloads. Layers whose data ships with the app contact "
        "nobody at all.",
        "When you turn a layer on and select a point.", "Every app with a map."))
    for a in apps:
        if not a["goatcounter"]:
            continue
        rows.append(recipient_row(
            "GoatCounter", "analytics", "https://www.goatcounter.com/help/privacy",
            "A page count and a few named events. See "
            '<a href="#analytics">Analytics, precisely</a>.',
            "Every visit; events as you use the map.",
            ", ".join(x["name"] for x in apps if x["goatcounter"]) + ".", once=True))
        break
    ga_users = [a["name"] for a in apps if a["ga"]]
    if ga_users:
        rows.append(recipient_row(
            "Google Analytics", "analytics", "https://policies.google.com/privacy",
            "A standard GA4 page view, including the page URL. Loaded <strong>only</strong> "
            "on the live site and <strong>never inside an embed</strong>.",
            "Every visit to the live site.", ", ".join(ga_users) + "."))
    return "\n".join(rows)


def recipient_row(label, sub, policy, what, when, who, once=False):
    name = ('<a href="%s" target="_blank" rel="noopener">%s</a>' % (esc(policy), esc(label))
            if policy else esc(label))
    return (
        "          <tr>\n"
        '            <td class="who">%s<small>%s</small></td>\n'
        "            <td>%s</td>\n"
        "            <td>%s</td>\n"
        '            <td class="which">%s</td>\n'
        "          </tr>" % (name, esc(sub), what, esc(when), esc(who)))


def render_storage_paragraphs(apps):
    """One sentence per DISTINCT key, naming the apps that set it."""
    by_key = {}
    for a in apps:
        for store in ("sessionStorage", "localStorage"):
            for k in a["storage"][store]:
                by_key.setdefault((store, k), []).append(a["name"])
    out = []
    for (store, key), users in sorted(by_key.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        if key.endswith("school-type-filter"):
            out.append(
                "<p><strong>One display preference, per app.</strong> The school layer's type "
                "filter is remembered in %s under %s on %s. It is a handful of true/false "
                "switches, it is erased when you close the tab, and it never leaves your "
                "browser.</p>" % (code(store), code(key), esc(joined(users))))
        elif key == "districtry-theme":
            out.append(
                "<p><strong>Light or dark.</strong> If you use the theme toggle, the choice is "
                "kept in %s under %s on %s, so the site does not flash white on your next "
                "visit. It is one word, and it never leaves your browser.</p>"
                % (code(store), code(key), esc(joined(users))))
        else:
            out.append(
                "<p><strong>%s.</strong> Stored in %s on %s. It never leaves your browser.</p>"
                % (code(key), code(store), esc(joined(users))))
    return "\n      ".join(out)


def render_apps_lede(apps):
    """The sentence introducing the per-app table, DERIVED from the same
    measurements the table's cells are.

    It used to be a hardcoded "one has a theme toggle, one runs Google
    Analytics and one runs no analytics at all", sitting directly above a
    paragraph boasting that every cell below is read out of the app it
    describes. By 2026-09-08 both of its countable claims were false: TWO apps
    run Google Analytics (Illinois and New York, into one property), and NO app
    runs no analytics at all, because every surface carries the shared
    GoatCounter. A privacy page that understates how many surfaces report to
    Google is a worse defect than a stale traffic figure, and it went wrong the
    ordinary way -- a literal next to a measurement, and only the measurement
    moved.
    """
    ga = [a for a in apps if a["ga"]]
    none = [a for a in apps if not a["goatcounter"] and not a["ga"]]
    bits = []
    if ga:
        bits.append("%s %s Google Analytics"
                    % (esc(joined(a["name"] for a in ga)),
                       "run" if len(ga) > 1 else "runs"))
    if none:
        bits.append("%s %s no analytics at all"
                    % (esc(joined(a["name"] for a in none)),
                       "run" if len(none) > 1 else "runs"))
    else:
        bits.append("every one of them carries the same counter")
    return "; ".join(bits) + "."


def render_analytics_section(apps):
    gc = [a for a in apps if a["goatcounter"]]
    ga = [a for a in apps if a["ga"]]
    none = [a for a in apps if not a["goatcounter"] and not a["ga"]]
    parts = []
    if none:
        parts.append(
            "<p>%s %s no analytics of any kind — no counter, no page view, no event.</p>"
            % (esc(joined(a["name"] for a in none)),
               "carry" if len(none) > 1 else "carries"))
    parts.append("<h3>GoatCounter</h3>")
    # Where the counts go is a CLAIM about arrangement, not just a list of names, so the
    # sentence has to follow the arrangement. The apps reported to separate sites until
    # 2026-08-24 and to one shared site after; a template that says "their own separate
    # site" while listing the same name four times is not a formatting wart, it is a false
    # statement on a privacy page. Both shapes are spelled out rather than interpolated.
    gc_sites = {a["goatcounter"]["site"] for a in gc}
    if len(gc_sites) == 1 and len(gc) > 1:
        where = ("%s all report to a single GoatCounter site (%s); the page path is what "
                 "distinguishes them" % (esc(joined(a["name"] for a in gc)),
                                         code(sorted(gc_sites)[0])))
    else:
        where = ("%s each report to their own separate GoatCounter site (%s)"
                 % (esc(joined(a["name"] for a in gc)),
                    ", ".join(code(a["goatcounter"]["site"]) for a in gc)))
    parts.append(
        '<p><a href="https://www.goatcounter.com/help/privacy" target="_blank" '
        'rel="noopener">GoatCounter</a> is cookieless and does not build a profile across '
        "sites. %s. Besides the "
        "page view, each app sends named events for: %s. Exactly two of those — %s — carry "
        "coordinates, <strong>rounded to %d decimal places</strong>. "
        "<strong>Nothing you type is ever sent to it.</strong></p>"
        % (where,
           esc(", ".join(EXPECTED_EVENTS)),
           esc(" and ".join(EXPECTED_COORD_EVENTS)), COORD_DECIMALS))
    parts.append("<h3>Google Analytics</h3>")
    if ga:
        parts.append(
            "<p>GA4 (%s) runs on %s — and <strong>only there</strong>: never on a local copy, "
            "never inside an iframe embed, and not at all on %s. It sets its own cookies and "
            "records the standard GA4 page view, which <strong>includes the page URL</strong> "
            "— so if you arrived on a shared permalink, the point encoded in that link is part "
            "of what Google sees. Google's handling is governed by "
            '<a href="https://policies.google.com/privacy" target="_blank" rel="noopener">its '
            "own privacy policy</a>.</p>"
            % (code(ga[0]["ga"]["id"]), esc(joined(a["name"] for a in ga)),
               esc(joined(a["name"] for a in apps if not a["ga"]))))
    else:
        parts.append("<p>No app here loads Google Analytics.</p>")
    parts.append(
        '<p class="cta-note">Blocking either one is fine. The analytics calls are written so '
        "that a blocked or failed counter is a no-op — nothing about the map changes.</p>")
    return "\n\n    ".join(parts)


def render_footer_links(apps):
    return "\n      ".join(
        '<a href="%s">%s</a>' % (esc(a["url"]), esc(a["name"]))
        for a in apps if a["tag"])


def _jsonld(title, desc):
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "WebPage",
        "@id": CANONICAL,
        "url": CANONICAL,
        "name": title,
        "description": desc,
        "inLanguage": "en-US",
        "isPartOf": {"@id": SITE + "#website"},
        "breadcrumb": {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "districtry", "item": SITE},
                {"@type": "ListItem", "position": 2, "name": "Privacy"},
            ],
        },
    }, indent=2)


def build():
    apps = load_apps()
    gate_point_transmission(apps)
    gate_fleet_claims(apps)

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

    title = "Privacy — districtry"
    desc = ("What districtry stores, what leaves your browser and to whom, and "
            "what it never collects — every app on the site. No accounts, no "
            "profiles, nothing sold.")

    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>%(title)s</title>
<meta name="description" content="%(desc)s" />
<meta name="robots" content="index, follow" />
<link rel="canonical" href="%(canonical)s" />
<meta name="theme-color" content="%(brand)s" />
<link rel="icon" href="/favicon.svg" type="image/svg+xml" />
<link rel="icon" href="/favicon-192.png" type="image/png" sizes="192x192" />
<link rel="icon" href="/favicon.ico" sizes="32x32" />
<link rel="apple-touch-icon" href="/apple-touch-icon.png" />
<meta property="og:type" content="article" />
<meta property="og:site_name" content="districtry" />
<meta property="og:title" content="%(title)s" />
<meta property="og:description" content="%(desc)s" />
<meta property="og:url" content="%(canonical)s" />
<meta property="og:image" content="%(site)sog-image.png" />
<meta property="og:image:width" content="1200" />
<meta property="og:image:height" content="630" />
<meta property="og:locale" content="en_US" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="%(title)s" />
<meta name="twitter:description" content="%(desc)s" />
<meta name="twitter:image" content="%(site)sog-image.png" />
<script type="application/ld+json">
%(jsonld)s
</script>
<!-- GENERATED by scripts/build_privacy_page.py, which MEASURES each app's own
     shipped index.html for the facts it states. Do NOT hand-edit: `--check`
     fails the build, and a hand-edit would be a claim about code that nothing
     verified. Change the app, then regenerate. -->
<script>
/* The theme a reader chose in an app carries to this page, and is applied
   before first paint so there is no white flash on the way into dark. Only the
   Illinois app writes this key today; for the others the media query below is
   what decides, and a blocked localStorage (private mode) falls through to the
   same place. */
(function () {
  try {
    var stored = localStorage.getItem("districtry-theme");
    if (stored === "dark" || stored === "light") {
      document.documentElement.setAttribute("data-theme", stored);
    }
  } catch (e) { /* blocked storage — prefers-color-scheme decides */ }
})();
</script>
<style>
%(fontface)s

:root {
  color-scheme: light dark;
%(light)s
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
%(dark)s
  }
}
:root[data-theme="dark"] {
%(dark)s
}

* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font: 400 16px/1.6 var(--font-body);
  -webkit-text-size-adjust: 100%%;
}
a { color: var(--brand-700); }
:focus-visible { outline: 3px solid var(--brand-600); outline-offset: 2px; }

.skip-link {
  position: absolute; left: -9999px; top: 0;
  background: var(--ink); color: var(--paper);
  padding: 10px 16px; z-index: 10; border-radius: 0 0 6px 0;
}
.skip-link:focus { left: 0; }

/* The masthead wears what engine/shared/styles-subpage.txt gives the twelve
   instance sub-pages — uppercase display title, pill actions, one accent rule
   under the bar — written in THIS page's token vocabulary rather than that
   one's. The two vocabularies are a real fork (the root pages speak
   --surface/--brand-*, the instance pages speak --panel/--accent) and merging
   them is a separate job; what a reader notices between two sub-pages is the
   header treatment, and that is now the same on all thirteen. */
.masthead {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  box-shadow: inset 0 -3px 0 0 var(--brand-600);
}
.masthead-inner {
  max-width: 940px; margin: 0 auto; padding: 22px 20px 24px;
  display: flex; flex-wrap: wrap; gap: 14px 24px;
  align-items: center; justify-content: space-between;
}
.masthead h1 { margin: 0; min-width: 0; }
.title-text {
  font: var(--font-heading-weight) clamp(27px, 3.4vw, 37px)/1 var(--font-heading);
  text-transform: uppercase; letter-spacing: 0.005em; color: var(--ink);
}
.title-row { display: flex; align-items: center; gap: 13px; }
.logo-mark { width: 34px; height: 34px; flex: 0 0 auto; color: var(--ink); }
.mk-blend { mix-blend-mode: multiply; }
:root[data-theme="dark"] .mk-blend { mix-blend-mode: screen; }
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) .mk-blend { mix-blend-mode: screen; }
}
.masthead h1 small {
  display: block; margin-top: 7px;
  font: 400 14px/1.5 var(--font-body); color: var(--muted); max-width: 54ch;
  text-transform: none; letter-spacing: 0;
}
.masthead-actions {
  display: flex; flex-wrap: wrap; align-items: center;
  justify-content: flex-end; gap: 8px; margin-left: auto;
}
.masthead-actions a {
  display: inline-flex; align-items: center;
  font: 600 13.5px/1 var(--font-body); white-space: nowrap;
  color: var(--muted); background: transparent;
  border: 1px solid var(--border); border-radius: 999px;
  padding: 9px 16px; text-decoration: none;
  transition: color .14s ease, border-color .14s ease, background .14s ease;
}
.masthead-actions a:hover, .masthead-actions a:focus-visible {
  color: var(--brand-700); border-color: var(--brand-600);
  background: var(--brand-tint);
}
@media (prefers-reduced-motion: reduce) { .masthead-actions a { transition: none; } }

main { max-width: 940px; margin: 0 auto; padding: 8px 20px 56px; }
section { margin: 34px 0 0; }
h2 {
  margin: 0 0 12px; font: var(--font-heading-weight) 23px/1.15 var(--font-heading);
  text-transform: uppercase; letter-spacing: 0.01em;
}
h3 { margin: 22px 0 6px; font-size: 16px; }
p { margin: 0 0 14px; max-width: 76ch; }
.updated { color: var(--muted); font-size: 14px; margin-top: 22px; }
.k {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.9em;
  background: var(--brand-tint); border: 1px solid var(--brand-border);
  border-radius: 4px; padding: 1px 5px; white-space: nowrap;
}
.card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-card); box-shadow: var(--shadow-card);
  padding: 18px 20px 6px;
}
.tldr { background: var(--brand-tint); border: 1px solid var(--brand-border);
  border-radius: var(--radius-card); padding: 18px 20px; margin-top: 6px; }
.tldr ul { margin: 10px 0 0; padding-left: 20px; }
.tldr li { margin: 0 0 8px; max-width: 74ch; }
.nope { margin: 0 0 14px; padding-left: 20px; }
.nope li { margin: 0 0 7px; max-width: 74ch; }
.table-wrap { overflow-x: auto; border: 1px solid var(--border);
  border-radius: var(--radius-card); background: var(--surface); }
table { border-collapse: collapse; width: 100%%; min-width: 720px; font-size: 14px; }
th, td { text-align: left; vertical-align: top; padding: 11px 14px;
  border-bottom: 1px solid var(--border-soft); }
thead th { background: var(--surface-2); font-size: 12px; text-transform: uppercase;
  letter-spacing: 0.04em; color: var(--ink-3); white-space: nowrap; }
tbody tr:last-child th, tbody tr:last-child td { border-bottom: 0; }
td small, th small { display: block; color: var(--faint); font-size: 12px;
  font-weight: 400; margin-top: 3px; text-transform: none; letter-spacing: 0; }
.who { white-space: nowrap; }
.which { color: var(--muted); }
.cta-note { color: var(--muted); font-size: 14px; }
.disclaimer { margin-top: 34px; padding-top: 18px; border-top: 1px solid var(--border);
  color: var(--muted); font-size: 14px; }

.site-footer { border-top: 1px solid var(--border); background: var(--surface); }
.footer-inner { max-width: 940px; margin: 0 auto; padding: 26px 20px 34px;
  color: var(--muted); font-size: 14px; }
.footer-links { display: flex; flex-wrap: wrap; gap: 8px 18px; margin-top: 10px; }

@media (max-width: 640px) {
  .title-text { font-size: 23px; }
  .logo-mark { width: 27px; height: 27px; }
  .masthead-inner { padding: 16px 16px 17px; }
  .masthead-actions { justify-content: flex-start; margin-left: 0; width: 100%%; gap: 6px; }
  .masthead-actions a { font-size: 12.5px; padding: 8px 13px; }
  main { padding: 4px 16px 44px; }
}
</style>
</head>
<body>

<a href="#page-main" class="skip-link">Skip to content</a>

<header class="masthead">
  <div class="masthead-inner">
    <h1>
      <span class="title-row">%(mark)s<span class="title-text">Privacy</span></span>
      <small>What districtry stores, what leaves your browser, and what it never collects.</small>
    </h1>
    <div class="masthead-actions">
      <a href="/">&larr; districtry</a>
      %(footerlinks)s
    </div>
  </div>
</header>

<main id="page-main" tabindex="-1">

  <section>
    <p class="updated">Last updated %(updated)s &middot; Applies to <strong>districtry.com</strong>
      and every app under it.</p>

    <div class="tldr">
      <p><strong>The short version.</strong> There is no account to make, no server of ours to
        store anything in, and nothing here is sold or used for advertising.</p>
      <ul>
        <li>Every app here is a <strong>static website</strong> — a set of files your browser
          downloads and then runs on its own. We operate no database and no back end.</li>
        <li><strong>The point you pick is not saved anywhere by us.</strong> It lives in your
          browser and in the address bar, so a refresh or a shared link can restore it.</li>
        <li>Where a counter runs, the only location it ever receives is
          <strong>rounded to about a kilometre</strong> — deliberately too coarse to identify
          an address.</li>
        <li>Looking things up means asking other people's servers — map tiles, address search,
          and the government GIS services each layer reads. Those servers see your IP address,
          as they would for any website.</li>
      </ul>
    </div>
  </section>

  <section>
    <h2>Which app you are on</h2>
    <p>districtry is one project serving several apps from one address, and they do not all
      behave identically — %(appslede)s Rather than flatten that into a vague sentence, here is
      each app's own row. <strong>Every cell is read out of the page that app actually
      serves</strong>, by the script that builds this one.</p>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th scope="col">App</th>
            <th scope="col">Google Analytics</th>
            <th scope="col">GoatCounter</th>
            <th scope="col">Stored in your browser</th>
            <th scope="col">Address search</th>
            <th scope="col">Sends your point to a server</th>
          </tr>
        </thead>
        <tbody>
%(approws)s
        </tbody>
      </table>
    </div>
  </section>

  <section>
    <h2>What stays on your device</h2>
    <p>All of it is yours to clear at any time through your browser's &#34;clear site data&#34;.</p>
    <div class="card">
      %(storage)s
      <p><strong>A cache of each app's own files.</strong> A service worker stores the app shell,
        boundary files and officeholder rosters locally so the map loads fast and works offline.
        It holds published public data — district shapes and rosters — not anything about you.</p>
      <p><strong>No app here sets a cookie of its own.</strong> Google Analytics, where it runs,
        sets its own.</p>
    </div>
  </section>

  <section>
    <h2>What leaves your browser, and who receives it</h2>
    <p>Every row here is something your browser requests directly. Each of those servers
      necessarily sees your IP address and the request itself; none of them receives a name, an
      email, or an account, because these apps have none to give.</p>

    <div class="table-wrap">
      <table>
        <thead>
          <tr><th scope="col">Who</th><th scope="col">What they receive</th>
              <th scope="col">When</th><th scope="col">Which apps</th></tr>
        </thead>
        <tbody>
%(recipients)s
        </tbody>
      </table>
    </div>
    <p class="cta-note">Each linked policy is that company's own; this page cannot speak for
      them. The full, machine-checked list of every dataset an app reads is on that app's
      sources page.</p>
  </section>

  <section>
    <h2>Your location</h2>
    <div class="card">
      <p>No app here asks for your location on its own. It is offered once, behind the
        <strong>&#34;Use my current location&#34;</strong> button, and your browser asks your
        permission before anything happens. Declining costs you nothing else on the page.</p>
      <p>If you allow it, the coordinates your browser reports are used <strong>in the
        page</strong> to drop a point and answer the layer cards. The one thing that goes
        anywhere is a <strong>rounded pair</strong> sent to that app's GoatCounter — %(dp)d
        decimal places, roughly a kilometre — which is coarse enough that it cannot pin an
        address and fine enough to show which part of a region the feature gets used from.</p>
      <p>Clicking the map is the same story with no permission needed: the point is yours, and
        only the rounded version is counted.</p>
    </div>
  </section>

  <section id="analytics">
    <h2>Analytics, precisely</h2>
    <p>Counters run for one reason: to know whether anyone is using this and which parts.</p>

    %(analytics)s
  </section>

  <section>
    <h2>Links you share, and reports you send</h2>
    <div class="card">
      <p><strong>Permalinks carry your point.</strong> Selecting a place writes it into the
        address bar as %(permalink)s, at full precision, along with the layers you have on. That
        is what makes a link shareable — and it means anyone you send the link to, and anything
        that logs it, gets that location. Delete the part of the URL after %(hash)s to share the
        map without it.</p>
      <p><strong>Bug reports are yours to send.</strong> &#34;Report a bug or leave a comment&#34;
        prepares a draft containing what you wrote, the current page URL — which may include your
        point — and your browser's user-agent string. It is only ever a draft: nothing is
        transmitted until you submit the GitHub issue or send the email yourself, and you can
        edit it first.</p>
    </div>
  </section>

  <section>
    <h2>What there isn't</h2>
    <ul class="nope">
      <li>No accounts, logins, or passwords.</li>
      <li>No database or back end operated by this project — there is nowhere for us to keep
        anything.</li>
      <li>No advertising, ad networks, retargeting pixels, or social trackers.</li>
      <li>No sale or sharing of data. There is no data of yours to sell.</li>
      <li>No cross-site tracking or profile built by this project.</li>
      <li>No collection of names, email addresses, or payment details — no app here has a field
        that asks for one.</li>
      <li>No unrounded location in any analytics event this project sends.</li>
    </ul>
    <p>Every app here is a single open-source page. If a claim on this page and the code ever
      disagree, the code is the truth and this page is the bug:
      <a href="%(repo)s" target="_blank" rel="noopener">read it, or file the discrepancy</a>.</p>
  </section>

  <section>
    <h2>Children</h2>
    <p>districtry is a general-audience civic reference. It has no sign-up, collects no personal
      details from anyone, and is not directed at children.</p>
  </section>

  <section>
    <h2>Changes, and how to ask</h2>
    <div class="card">
      <p>This page is versioned with the apps it describes, and it is <em>generated from them</em>
        — the build reads each app's own shipped page for the facts in the tables above, and
        refuses to publish a claim that has stopped being true. When the data flows change, this
        page changes in the same commit:
        <a href="%(repo)s/commits/main/privacy.html" target="_blank" rel="noopener">the file's
        history</a> is the changelog.</p>
      <p>Questions, corrections, or a request about your data:
        <a href="mailto:%(contact)s?subject=districtry%%20%%E2%%80%%94%%20privacy">%(contact)s</a>.
        Because the project stores nothing about you, there is generally nothing to look up,
        correct, or delete on our side — but if you think that is wrong in your case, say so and
        it will be checked properly rather than waved away.</p>
    </div>
  </section>

  <p class="disclaimer"><strong>Not legal advice, and not a contract.</strong> This page describes
    how the software behaves, verified against the source. It is a plain-language description, not
    a warranty, and it does not change the disclaimers on the maps themselves.</p>

</main>

<footer class="site-footer">
  <div class="footer-inner">
    <p>districtry answers one question: which civic districts contain the point you picked, and
      who represents you there. It reads public data, cites its sources, and never guesses an
      officeholder.</p>
    <div class="footer-links">
      <a href="/">&larr; districtry</a>
      %(footerlinks)s
      <a href="https://overberg.co/why/" target="_blank" rel="noopener">Why this exists</a>
      <a href="%(repo)s" target="_blank" rel="noopener">View source on GitHub</a>
    </div>
  </div>
</footer>

</body>
</html>
""" % {
        "title": esc(title),
        "desc": esc(desc),
        "jsonld": _jsonld(title, desc),
        "canonical": CANONICAL,
        "site": SITE,
        "brand": light["brand-600"].strip(),
        "favicon": esc(favicon_uri),
        "fontface": fontface + "\n" + FALLBACK_FACE,
        "light": token_css(LIGHT_TOKENS, light, ":root"),
        "dark": token_css(DARK_TOKENS, dark, '[data-theme="dark"]', DARK_EXTRA,
                          indent="    "),
        "mark": load_mark(),
        "updated": UPDATED,
        "approws": render_app_rows(apps),
        # ALL the apps, not just the mapped ones: the geocoder rows name which
        # surfaces reach each host, and the front door reaches one now.
        "recipients": render_recipient_rows(apps),
        "storage": render_storage_paragraphs(apps),
        "appslede": render_apps_lede(apps),
        "analytics": render_analytics_section(apps),
        "footerlinks": render_footer_links(apps),
        "permalink": code("#point=41.88250,-87.62850"),
        "hash": code("#"),
        "dp": COORD_DECIMALS,
        "repo": REPO_URL,
        "contact": CONTACT,
    }


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="verify the committed privacy.html matches; exit 1 on drift")
    args = ap.parse_args()

    rendered = build()

    if args.check:
        try:
            with open(OUT, encoding="utf-8", newline="") as f:
                current = f.read()
        except OSError as e:
            fail("cannot read privacy.html: %s" % e)
        if current != rendered:
            for dl in list(difflib.unified_diff(
                    current.splitlines(), rendered.splitlines(),
                    fromfile="committed privacy.html", tofile="regenerated",
                    lineterm="", n=1))[:40]:
                print("  " + dl, file=sys.stderr)
            fail("privacy.html has drifted from what the apps actually do. This page "
                 "is a set of claims about code — regenerate it rather than editing "
                 "the claim, and if the new page reads wrong, the APP changed.")
        print("build-privacy-page: OK — privacy.html matches all %d app(s) as shipped"
              % len(load_apps()))
        return

    with open(OUT, "w", encoding="utf-8", newline="") as f:
        f.write(rendered)
    print("build-privacy-page: wrote privacy.html — %d app(s) measured, %d bytes"
          % (len(load_apps()), len(rendered)))


if __name__ == "__main__":
    main()
