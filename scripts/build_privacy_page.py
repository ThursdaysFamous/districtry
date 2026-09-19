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

ONE CLAIM IS MEASURED ACROSS THE WHOLE TREE, AND IT HAD TO BE. The recipients
table said GoatCounter received from "the front door, Illinois, New York City,
San Francisco, Wisconsin, Iowa and Michigan" — the seven files this generator
reads — while the counter is in fact on every page of the site, put there by the
phase-2 rollout. Seven surfaces named against 243 counted. The GoatCounter row
is now measured through `validate_analytics.py`, which already discovers the
pages and already records the two pages that deliberately carry no counter; see
COUNTER_EXCEPTIONS below for what is gated and what is left unstated.

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

def shared_footer_byline(indent=""):
    """The author byline, read from its ONE source.

    engine/shared/footer-byline.txt is shared with the nineteen authored pages
    that carry it as an ENGINE fence spliced by compose_app.py. A GENERATED page
    reads it here instead of carrying a fence, because a fence would have to
    agree with whatever this builder emits inside it -- which means reading the
    file anyway, with an ordering dependency between the two tools on top. One
    source, two mechanisms; that file's own comment says the same thing from the
    other side.

    The block's leading HTML comment is for a reader of the engine tree and is
    dropped here, so the published page carries the markup alone.
    """
    path = os.path.join(REPO_ROOT, "engine", "shared", "footer-byline.txt")
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    markup = re.sub(r"(?s)^\s*<!--.*?-->\s*", "", text).strip()
    return "\n".join(indent + ln.strip() for ln in markup.splitlines())

def shared_goatcounter(indent=""):
    """The counter tag, read from its ONE source.

    Same contract as shared_footer_byline above and for the same reason: the
    authored pages take engine/shared/goatcounter.txt as an ENGINE fence, a
    GENERATED page reads the file here, and the leading comment is for a reader
    of the engine tree rather than the published page.
    """
    path = os.path.join(REPO_ROOT, "engine", "shared", "goatcounter.txt")
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    markup = re.sub(r"(?s)^\s*<!--.*?-->\s*", "", text).strip()
    return "\n".join(indent + ln.strip() for ln in markup.splitlines())


def shared_theme_boot():
    """The theme boot, read from its ONE source.

    Same contract again, with one difference: this block is JAVASCRIPT rather
    than markup, so its leading comment is part of the block a reader of the
    published page is served, and its indentation is load-bearing. It is
    returned verbatim -- the authored pages take engine/shared/theme-boot.txt
    as an ENGINE fence and get the same bytes from compose_app.py.

    The copy this replaced applied a stored choice and left the OS preference
    to the media query, and set no theme-colour at all.
    """
    path = os.path.join(REPO_ROOT, "engine", "shared", "theme-boot.txt")
    with open(path, encoding="utf-8") as fh:
        return fh.read().rstrip("\n")


def shared_mono_faces():
    """The self-hosted IBM Plex Mono face, read from its ONE source.

    Same contract as the two above. The design system's --font-mono names
    Plex for its disambiguated zero, which is doing real work under the
    dataset ids, urls and workflow filenames these pages set in it; a page
    that names the family and defines no face falls through to whatever mono
    the reader's OS supplies, which is the state every root page was in until
    2026-09-18.
    """
    path = os.path.join(REPO_ROOT, "engine", "shared", "mono-faces.txt")
    with open(path, encoding="utf-8") as fh:
        return fh.read().rstrip("\n")


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
    "font-heading", "font-heading-weight", "font-body", "font-mono",
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

# THE BATCH ADDRESS CHECK (Illinois today) is a second way an address leaves a
# browser, and a materially different one: a reader who pastes a petition sheet
# is sending OTHER PEOPLE's addresses, not their own, and sending a few hundred
# of them rather than one. A geocoder row describing only a search box would be
# true of what it says and silent about the larger flow, so the row names the
# surfaces that have such a panel and says what it sends.
#
# THREE markers, all required. A partial match means a rename got half way —
# and the failure that would cause is the disclosure going quiet while the
# panel keeps sending, so some-but-not-all FAILS rather than measuring false.
ADDRESS_LIST_MARKERS = ('id="batch-modal"', 'id="batch-input"', "wireBatchCheck(")


def measure_address_list(src, name):
    """Which geocoder hosts the batch address panel sends a pasted list to.

    Sliced out of the panel's OWN function rather than searched for across the
    file. An app reaches several geocoders for different jobs — Illinois reaches
    Photon for the list and Nominatim for office pins — so a file-wide search
    would have the pin geocoder confessing to a transmission it never receives.
    """
    hits = [m for m in ADDRESS_LIST_MARKERS if m in src]
    if not hits:
        return []
    if len(hits) != len(ADDRESS_LIST_MARKERS):
        fail("%s carries %d of the %d batch-address-check markers (%s). A partial "
             "match is a half-finished rename: fix the markers, because the "
             "geocoder row below stops naming this surface while it goes on "
             "sending pasted lists."
             % (name, len(hits), len(ADDRESS_LIST_MARKERS), ", ".join(hits)))
    start = src.find("(function wireBatchCheck()")
    end = src.find("\n  })();", start)
    block = src[start:end if end > start else len(src)]
    hosts = sorted(h for h in GEOCODERS if h in block)
    if not hosts:
        fail("%s ships a batch address check that reaches none of the known "
             "geocoders — either it found a new one (add it to GEOCODERS) or the "
             "slice above no longer covers the panel's own code." % name)
    return hosts


# FLEET CLAIMS — stated once on the page, and required to be identical. The
# tuple is what the measurement must return for EVERY app that has a map.
# `metro-portal/` (the sibling-metro CARD was shown) left the vocabulary on
# 2026-08-25 when the card did: the handoff is a silent redirect now, so the
# only portal event an app can send is the departure itself.
# `compare/` and `compare-stop` joined on 2026-09-18, when the district
# comparison control was finally counted: the app had instrumented eleven
# actions since it shipped and that was not one of them, so whether readers
# used the feature was an inference rather than a measurement.
# `copy-coordinates`, `embed-iframe` and `share-permalink` joined on 2026-09-19,
# and had been sent by every app since the share popover shipped. They reach
# `trackEvent` through `shareCopyButton(label, getText, eventName)`, so the name
# is a PARAMETER at the point of the call and the old literal-matching
# measurement could not see them — this page published ten events while every
# app sent thirteen. Note what did NOT change: `EXPECTED_COORD_EVENTS` is still
# two. `shareCopyButton` calls `trackEvent` with ONE argument, so these three
# send a name and nothing else. The text a reader copies contains their point;
# the event recording that they copied it does not.
EXPECTED_EVENTS = ["address-search", "compare-stop", "compare/",
                   "copy-coordinates", "embed-iframe", "geolocate",
                   "geolocate-success", "layer/", "metro-portal-go/", "select",
                   "share-native", "share-open", "share-permalink"]
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

    # WRITES AND READS ARE MEASURED APART, and that distinction is the whole
    # accuracy of the sentence this feeds. The pattern used to match
    # get|set|removeItem together, which was right while the only surfaces
    # touching a key were the ones that wrote it: every app has a theme toggle,
    # so every app both set and read `districtry-theme`. The front door gained
    # the shared theme boot on 2026-09-18 and READS that key without ever
    # writing one — it has no toggle — and a measurement that could not tell
    # the two apart published "the choice is kept ... on The front door",
    # which claims a store this site does not make there.
    storage = {}
    reads = {}
    for store in ("sessionStorage", "localStorage"):
        key_re = r"\(\s*([A-Za-z_$][\w$]*|\"[^\"]*\"|'[^']*')"
        # NOT named `read`: this module already has a read() helper and this
        # function calls it, so a local of that name makes the earlier call an
        # unbound local.
        wrote, read_only = set(), set()
        for mm in re.finditer(store + r"\.(?:set|remove)Item" + key_re, src):
            wrote.add(resolve_key(src, mm.group(1)))
        for mm in re.finditer(store + r"\.getItem" + key_re, src):
            read_only.add(resolve_key(src, mm.group(1)))
        storage[store] = sorted(wrote)
        reads[store] = sorted(read_only - wrote)
    app["storage"] = storage
    app["storage_read"] = reads

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
    app["address_list_hosts"] = measure_address_list(src, app["name"])

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

    app["events"], app["indirect"] = collect_events(src, app["file"])
    app["coord_events"] = sorted({mm.group(1) for mm in re.finditer(
        r"trackEvent\(\s*[\"']([^\"']+)[\"']\s*,\s*\w+\.toFixed\((\d)\)", src)})
    app["coord_decimals"] = sorted({int(mm.group(1)) for mm in re.finditer(
        r"trackEvent\(\s*[\"'][^\"']+[\"']\s*,\s*\w+\.toFixed\((\d)\)", src)})
    return app


# ---------------------------------------------------------------------------
# Reading the event vocabulary out of an app
#
# THE FIRST VERSION OF THIS MATCHED A STRING LITERAL AFTER `trackEvent(` AND
# PUBLISHED WHAT IT FOUND, which meant a call it could not read was a call it
# did not count. Measured 2026-09-19, every app sends THIRTEEN named events and
# this page published TEN: `share-permalink`, `embed-iframe` and
# `copy-coordinates` reach `trackEvent` through `shareCopyButton(label, getText,
# eventName)`, so the name at the call site is a PARAMETER and the literal sits
# one frame away. The page whose whole standard is naming what leaves a reader's
# browser was understating its own app by three events.
#
# This is the `registerCountyLayer` shape a third time — a helper that receives
# or closes over the thing a regex is looking for — and the lesson those two
# already paid for is that the DANGEROUS failure is the silent one. So the rule
# here is not "read one more level"; it is that an unreadable call is an ERROR.
# Resolution handles exactly one hop, because that is what the app does; a
# second hop, a computed name, or a helper whose call sites disagree FAILS and
# names the line, which is the state a person can act on. An indirect call that
# quietly resolved to nothing is the state nobody can see.
#
# What is deliberately NOT done: following `"prefix/" + expr`. Those already
# work, because the published vocabulary names the PREFIX (`layer/`,
# `compare/`, `metro-portal-go/`) rather than the per-layer suffix, and the
# literal is right there at the call site.

def split_args(text):
    """Top-level comma split of a call's argument text. Depth-aware, string-aware."""
    out, buf, depth, quote = [], [], 0, None
    i = 0
    while i < len(text):
        c = text[i]
        if quote:
            if c == "\\":
                buf.append(c)
                i += 1
                if i < len(text):
                    buf.append(text[i])
                i += 1
                continue
            if c == quote:
                quote = None
        elif c in "\"'":
            quote = c
        elif c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == "," and depth == 0:
            out.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(c)
        i += 1
    out.append("".join(buf))
    return [a.strip() for a in out]


def call_args(src, open_paren):
    """Argument text of the call whose '(' is at open_paren, or None if unbalanced."""
    depth, quote, i = 0, None, open_paren
    while i < len(src):
        c = src[i]
        if quote:
            if c == "\\":
                i += 2
                continue
            if c == quote:
                quote = None
        elif c in "\"'":
            quote = c
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return src[open_paren + 1:i]
        i += 1
    return None


LITERAL_RE = re.compile(r"""^["']([^"']+)["']""")
IDENT_RE = re.compile(r"^[A-Za-z_$][\w$]*$")


def enclosing_function(src, pos):
    """The nearest `function NAME(params)` textually before pos, as (name, [params])."""
    best = None
    for m in re.finditer(r"\bfunction\s+([A-Za-z_$][\w$]*)\s*\(([^)]*)\)", src):
        if m.start() < pos:
            best = m
        else:
            break
    if not best:
        return None
    params = [p.strip() for p in best.group(2).split(",") if p.strip()]
    return best.group(1), params


def collect_events(src, where):
    """Every event name an app can send, with indirect calls RESOLVED not skipped.

    Returns (sorted names, [(helper, param, [names]) ...]). Fails the build on a
    `trackEvent(` call whose name it cannot establish.
    """
    names, indirect = set(), []
    for m in re.finditer(r"\btrackEvent\s*\(", src):
        # the definition itself is not a call
        if re.search(r"function\s+trackEvent\s*$", src[:m.end() - 1].rstrip()):
            continue
        args = call_args(src, m.end() - 1)
        line = src.count("\n", 0, m.start()) + 1
        if args is None:
            fail("%s line %d: cannot read the arguments of a trackEvent call. "
                 "This page names every event an app sends, so a call it cannot "
                 "read is not one it may skip." % (where, line))
        first = split_args(args)[0]
        lit = LITERAL_RE.match(first)
        if lit:
            names.add(lit.group(1))
            continue
        if not IDENT_RE.match(first):
            fail("%s line %d: trackEvent is called with %r, which is neither a "
                 "string literal nor a plain parameter name, so the event it "
                 "sends cannot be established statically. Either name the event "
                 "with a literal or measure this page's event list in a browser."
                 % (where, line, first))
        fn = enclosing_function(src, m.start())
        if not fn or first not in fn[1]:
            fail("%s line %d: trackEvent is called with the identifier %r, and "
                 "it is not a parameter of the function it sits in, so the "
                 "event name cannot be followed to its call sites."
                 % (where, line, first))
        helper, params = fn
        idx = params.index(first)
        found = set()
        for c in re.finditer(r"\b%s\s*\(" % re.escape(helper), src):
            call = call_args(src, c.end() - 1)
            if call is None:
                continue
            parts = split_args(call)
            if len(parts) <= idx:
                continue
            cl = LITERAL_RE.match(parts[idx])
            if cl:
                found.add(cl.group(1))
        if not found:
            fail("%s line %d: trackEvent takes its name from %s()'s parameter "
                 "%r and no call to %s() passes a string literal there, so no "
                 "event name can be established."
                 % (where, line, helper, first, helper))
        names |= found
        indirect.append((helper, first, sorted(found)))
    return sorted(names), indirect


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


# EVERY PAGE ON THIS SITE CARRIES THE COUNTER, NOT JUST THE APPS, and until
# 2026-09-16 this page said otherwise. The recipients table named GoatCounter's
# surfaces as the seven measured below -- the six apps and the front door --
# because those are the only files this generator reads. The phase-2 rollout put
# the tag on every page: the per-county board pages, the question pages, the
# history pages, and this page itself. So the table understated its own
# recipient, on the page whose whole standard is that whoever receives your IP
# address is named.
#
# The fix is to measure the tree rather than to widen a list, and to measure it
# THROUGH validate_analytics: that gate already discovers the pages, already
# knows which are redirect shells, and already records the two deliberate
# exceptions. Two readers of one question is where this fleet's recurring defect
# starts, so there is one reader and this page borrows it.
#
# The reader-facing reason for each exception is written here rather than taken
# from NO_COUNTER, whose reasons address a developer -- but the NAMES are gated
# against it, so this page cannot name an exception the tree does not have.
# Spelled out because the page is prose. A number past this table would be a
# count of exceptions rather than of pages, so digits are fine as a fallback.
COUNT_WORDS = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five"}
COUNTER_EXCEPTIONS = {
    "404.html": "served for a URL that does not exist",
    "coverage-map.html":
        "the front door\u2019s iframe body, counted by the page that embeds it",
}


def measure_counter_coverage(apps):
    """Which pages on this site carry the GoatCounter tag.

    NO COUNT IS PUBLISHED, deliberately. The number moves every time a county
    ships, and a privacy claim that has to be regenerated for an unrelated change
    is one somebody will eventually regenerate without reading. The page states
    the SHAPE -- every page, bar the two named exceptions -- which is stable, and
    this measurement is what holds it true.
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        import validate_analytics as va
    except ImportError as e:
        fail("cannot import scripts/validate_analytics.py (%s). This page's "
             "GoatCounter row is measured through it so the two cannot disagree "
             "about which pages exist or which carry the tag." % e)
    surface, _tags = va.pages()
    counted, uncounted = [], []
    for _tag, rel, path in surface:
        with open(path, encoding="utf-8") as f:
            page = f.read()
        if va.REDIRECT_SHELL.search(page):
            continue
        (counted if va.GC_TAG.search(page) else uncounted).append(rel)

    if not counted:
        fail("no page on this site carries the GoatCounter tag, and the "
             "recipients table names it — either the fleet changed or this "
             "measurement is broken")
    stray = sorted(set(uncounted) - set(COUNTER_EXCEPTIONS))
    if stray:
        fail("%s carries no GoatCounter tag and this page tells a reader every "
             "page does. Either count it, or record it in COUNTER_EXCEPTIONS "
             "here and in NO_COUNTER in scripts/validate_analytics.py."
             % ", ".join(stray))
    back = sorted(set(COUNTER_EXCEPTIONS) - set(uncounted))
    if back:
        fail("%s now carries the counter and COUNTER_EXCEPTIONS still names it "
             "as an exception — drop the entry, here and in NO_COUNTER."
             % ", ".join(back))
    if sorted(COUNTER_EXCEPTIONS) != sorted(va.NO_COUNTER):
        fail("COUNTER_EXCEPTIONS names %s and validate_analytics.NO_COUNTER "
             "names %s. They are one claim written for two readers and must "
             "name the same pages."
             % (sorted(COUNTER_EXCEPTIONS), sorted(va.NO_COUNTER)))

    # The two measurements must also agree about the seven files they BOTH read.
    # This generator finds GoatCounter by its URL and the shared gate finds it by
    # the script tag; a disagreement means one of them is wrong about a page a
    # reader is served, which is the case neither can see alone.
    have = set(counted)
    for a in apps:
        mine, theirs = bool(a["goatcounter"]), a["file"] in have
        if mine != theirs:
            fail("%s: this page measures GoatCounter as %s and "
                 "scripts/validate_analytics.py measures it as %s. One of the "
                 "two readers is wrong about a page a reader is served."
                 % (a["file"], "present" if mine else "absent",
                    "present" if theirs else "absent"))
    return {"counted": counted, "uncounted": uncounted}


def counter_who():
    """The recipients table's "which surfaces" cell for GoatCounter.

    Plain text: recipient_row escapes this column.
    """
    bits = ["%s (%s)" % (rel, why) for rel, why in sorted(COUNTER_EXCEPTIONS.items())]
    n = len(bits)
    return ("Every page on this site — the apps, the front door, and every page "
            "they link. %s carr%s none: %s."
            % (COUNT_WORDS.get(n, str(n)), "ies" if n == 1 else "y", joined(bits)))


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
        # A key this surface only READS is named too, because a reader asking
        # what a page does with their browser storage is owed the read as well
        # as the write — but it is never labelled "kept", which would claim a
        # store that does not happen here.
        for store in ("sessionStorage", "localStorage"):
            for k in a["storage_read"][store]:
                stored.append("%s<small>read only</small>" % code(k))
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
        when = ("Only while you are searching for an address, or when a "
                "card places an office pin.")
        # MEASURED per (surface, host), not per surface: an app reaches more
        # than one geocoder, and only the one the batch panel actually calls
        # receives a pasted list.
        listers = [a["name"] for a in apps if host in a["address_list_hosts"]]
        if listers:
            what += (" <strong>%s</strong> also offer%s a batch check for people working "
                     "from a list — a petition sheet, a canvass list. That sends "
                     "<strong>every address in the list you paste</strong>, one lookup a "
                     "second until it is done. Those are usually other people&#39;s "
                     "addresses rather than your own, and the list itself is never "
                     "uploaded anywhere: it stays in your browser, and only the address "
                     "text goes to this geocoder." % (
                         esc(", ".join(listers)), "" if len(listers) > 1 else "s"))
            when += " A batch check sends its whole list, one address a second."
        rows.append(recipient_row(label, sub, policy, what, when,
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
    # NOT a list of the apps. Every page here carries the counter, so naming the
    # seven surfaces this generator reads would have understated the recipient —
    # see COUNTER_EXCEPTIONS. The WHEN column separates the two things that are
    # sent, because they do not come from the same set of pages: every page sends
    # a page view, and only an app's map sends a named event.
    if any(a["goatcounter"] for a in apps):
        rows.append(recipient_row(
            "GoatCounter", "analytics", "https://www.goatcounter.com/help/privacy",
            "A page count and a few named events. See "
            '<a href="#analytics">Analytics, precisely</a>.',
            "Every visit to any page. The named events come from an app\u2019s map "
            "only.", counter_who(), once=True))
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
            # `users` is the surfaces that WRITE the key, which is what "kept"
            # means; the surfaces that only read it are named separately,
            # because that is how the choice follows a reader off the map.
            readers = sorted(a["name"] for a in apps
                             if key in a["storage_read"].get(store, []))
            # NAMES THE MEASURED SURFACES, never "every other page": this
            # generator reads the seven surfaces in metros.json plus the root,
            # and the site's other pages are outside what it measures. A
            # sentence claiming all of them would be a claim this page cannot
            # check, on the page whose whole standard is that it checks.
            carried = (" %s read%s it and never write%s it, which is how the choice "
                       "follows you off the map."
                       % (esc(joined(readers)), "" if len(readers) > 1 else "s",
                          "" if len(readers) > 1 else "s")) if readers else ""
            out.append(
                "<p><strong>Light or dark.</strong> If you use the theme toggle, the choice is "
                "kept in %s under %s on %s, so the site does not flash white on your next "
                "visit. It is one word, and it never leaves your browser.%s</p>"
                % (code(store), code(key), esc(joined(users)), carried))
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
        where = ("Every page on this site reports to a single GoatCounter site "
                 "(%s) — the apps, the front door, and the text pages that answer "
                 "one question or list one county\u2019s board; the page path is what "
                 "distinguishes them" % code(sorted(gc_sites)[0]))
    else:
        where = ("%s each report to their own separate GoatCounter site (%s)"
                 % (esc(joined(a["name"] for a in gc)),
                    ", ".join(code(a["goatcounter"]["site"]) for a in gc)))
    parts.append(
        '<p><a href="https://www.goatcounter.com/help/privacy" target="_blank" '
        'rel="noopener">GoatCounter</a> is cookieless and does not build a profile across '
        "sites. %s. Besides the "
        "page view, each app sends named events for: %s. Exactly two of those — %s — carry "
        "coordinates, <strong>rounded to %d decimal places</strong>. A page that is not an "
        "app — a county list, a question page, this one — sends the page view and nothing "
        "else. <strong>Nothing you type is ever sent to it.</strong></p>"
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
        "author": { "@type": "Person", "@id": "https://districtry.com/#author", "name": "Adam Overberg", "url": "https://overberg.co", "email": "hello@overberg.co" },
        "isPartOf": {"@id": SITE + "#website"},
        "breadcrumb": {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "districtry", "item": SITE},
                {"@type": "ListItem", "position": 2, "name": "Privacy"},
            ],
        },
    }, indent=2)


# ——— THE ROOT PAGES' SHARED SHELL ———
#
# Everything outside <main>: the head, the tokens, the whole stylesheet, the
# masthead and the footer. It was inlined in build() and read as this page's
# own until 2026-09-15, when /about.html needed the same shell and the choice
# was between a second copy and one function. A second copy of 350 lines of
# head and CSS is how the fleet came to carry four hand-kept palettes.
#
# render_page() takes the four things a page owns — its masthead title, the
# line under it, the comment naming its generator, and its <main> — and every
# other value here is read from the file that owns it.
SHELL_HEAD = """<!DOCTYPE html>
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
%(goatcounter)s
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
%(generator)s
<script>
%(themeboot)s
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
code { font-family: var(--font-mono); }
.k {
  font-family: var(--font-mono); font-size: 0.9em;
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
      <span class="title-row">%(mark)s<span class="title-text">%(pagetitle)s</span></span>
      <small>%(pagesub)s</small>
    </h1>
    <div class="masthead-actions">
      <a href="/">&larr; districtry</a>
      %(footerlinks)s
    </div>
  </div>
</header>

<main id="page-main" tabindex="-1">
"""

SHELL_TAIL = """
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
%(byline)s
    </div>
  </div>
</footer>

</body>
</html>"""

PRIVACY_BODY = """
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
"""


def render_page(pagetitle, pagesub, generator, body, title, desc, jsonld,
                footerlinks, canonical=None, extra=None):
    """One root page, shell and all. `extra` carries a page's own %(key)s slots."""
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

    slots = {
        "byline": shared_footer_byline("        "),
        "title": esc(title),
        "desc": esc(desc),
        "jsonld": jsonld,
        "canonical": canonical or CANONICAL,
        "site": SITE,
        "brand": light["brand-600"].strip(),
        "favicon": esc(favicon_uri),
        "fontface": fontface + "\n" + FALLBACK_FACE + "\n" + shared_mono_faces(),
        "themeboot": shared_theme_boot(),
        "light": token_css(LIGHT_TOKENS, light, ":root"),
        "dark": token_css(DARK_TOKENS, dark, '[data-theme="dark"]', DARK_EXTRA,
                          indent="    "),
        "mark": load_mark(),
        "pagetitle": esc(pagetitle),
        "pagesub": esc(pagesub),
        "generator": generator,
        "footerlinks": footerlinks,
        # THE COUNTER. privacy.html read as counted until 2026-09-15 and was
        # not: scripts/validate_analytics.py matched the string `goatcounter`
        # anywhere on a page, and this page names the URL in its own recipients
        # TABLE as documentation. A gate that greps for a host credits a page
        # for describing it; the tag is what counts, and now both this page and
        # /about.html carry one.
        "goatcounter": shared_goatcounter(),
        "repo": REPO_URL,
        "contact": CONTACT,
    }
    slots.update(extra or {})
    # The trailing newline the template literal carried before the shell was
    # extracted: `lines[start+1:end]` dropped the blank line that sat between
    # </html> and the closing quotes.
    return ((SHELL_HEAD + body + SHELL_TAIL) % slots) + "\n"


def build():
    apps = load_apps()
    gate_point_transmission(apps)
    gate_fleet_claims(apps)
    measure_counter_coverage(apps)

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

    generator = ("<!-- GENERATED by scripts/build_privacy_page.py, which MEASURES each app's own\n"
                 "     shipped index.html for the facts it states. Do NOT hand-edit: `--check`\n"
                 "     fails the build, and a hand-edit would be a claim about code that nothing\n"
                 "     verified. Change the app, then regenerate. -->")
    return render_page(
        pagetitle="Privacy",
        pagesub="What districtry stores, what leaves your browser, and what it never collects.",
        generator=generator,
        body=PRIVACY_BODY,
        title=title, desc=desc, jsonld=_jsonld(title, desc),
        footerlinks=render_footer_links(apps),
        extra={
            "updated": UPDATED,
            "approws": render_app_rows(apps),
            # ALL the apps, not just the mapped ones: the geocoder rows name which
            # surfaces reach each host, and the front door reaches one now.
            "recipients": render_recipient_rows(apps),
            "storage": render_storage_paragraphs(apps),
            "appslede": render_apps_lede(apps),
            "analytics": render_analytics_section(apps),
            "permalink": code("#point=41.88250,-87.62850"),
            "hash": code("#"),
            "dp": COORD_DECIMALS,
        })


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
