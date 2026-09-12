#!/usr/bin/env python3
"""
Generate the per-fork GENERATED regions from metro-worksheet.json
(docs/MECHANIZATION_PLAYBOOK.md, Conversion 2).

Every fact a human used to hand-copy between per-fork files lives ONCE in
metro-worksheet.json (validated against schema/metro-worksheet.schema.json
before any file is touched). This script renders those facts into fenced
regions, marked like the engine's fences but generator-owned:

    /* ==== GENERATED:BEGIN <name> ==== */     (JS / CSS)
    <!-- ==== GENERATED:BEGIN <name> ==== -->  (HTML / Markdown)
    # ==== GENERATED:BEGIN <name> ====         (Python / YAML)
    // ==== GENERATED:BEGIN <name> ====        (JS line style)

Targets (region name -> file):
    metro-config      -> index.html   (interior of the METRO config fence)
    layer-area-rank   -> index.html   (the LAYER_AREA_RANK array)
    sw-metro-config   -> sw.js        (CACHE_NAME + shell/geometry/roster lists)
    validator-config  -> scripts/validate_index.py (floors + expected ids)
    smoke-config      -> scripts/smoke_test.mjs    (anchor/negative points, counts)
    metro-facts       -> CLAUDE.md    (city / geocoder / ground-truth / workflows)
    metro-header      -> README.md    (title + tagline)

Opt-in targets, emitted only when the worksheet carries the key that turns them
on (a fork without the key sees a byte-identical file and an untouched gate):
    verified-date     -> index.html   (the footer's date, rendered INTO the element;
                                       key: verified_date)
    perf-config       -> the performance harness's anchor point + offline layer
                                       list, which must mirror smoke-config
                                       (key: perf_profile)
    sources-verified  \
    source-credits     >  the public sources page (key: sources_page)
    layer-matrix      /   — the credits row that used to live in the footer, and
                            one matrix row per registered layer
    head-analytics    \
    head-brand         \
    head-theme          \  brand-as-data (key: brand — docs/DEV_PROCESS_ASSESSMENT.md
    brand-palette       /  stage R1): every brand-bearing surface in index.html,
    masthead-brand     /   plus METRO_BRAND on the metro-config region; with
    goatcounter       /    sources_page also set, the sources page's :root accents
    sources-palette  /     (sources-palette) join too

Modes:
    python3 scripts/generate_metro_files.py           # splice regions in place
    python3 scripts/generate_metro_files.py --check   # regenerate + diff; exit 1
                                                      # on any drift (the CI gate)
    python3 scripts/generate_metro_files.py --sync-fleet [SRC]
        # Conversion 3: refresh the worksheet's metro_explorers from the fleet
        # manifest (SRC = a metros.json path or URL; default: the repo-root
        # metros.json if present, else https://chidistricts.com/metros.json),
        # then regenerate. Only the metro_explorers value is rewritten — the
        # rest of the worksheet is untouched. Plain runs and --check never
        # touch the network, so the CI gate stays hermetic; launching a new
        # metro is a --sync-fleet regeneration PR in each fork.

Hand-editing a GENERATED region is a CI failure, not a review nit: edit the
worksheet and regenerate. Hand-written content outside the fences is never
touched. Dependencies: stdlib + jsonschema (pinned in scripts/requirements.txt).
"""

import argparse
import difflib
import functools
import datetime
import json
import os
import re
import sys

try:
    import jsonschema
except ImportError:
    print("generate-metro-files: FAIL — jsonschema is not installed "
          "(pip install -c scripts/requirements.txt jsonschema)", file=sys.stderr)
    sys.exit(1)

GENERATED_RE = re.compile(
    r"^[ \t]*(?:/\*|<!--|#|//)?[ \t]*==== GENERATED:(BEGIN|END) ([a-z0-9][a-z0-9-]*) ====[ \t]*(?:\*/|-->)?[ \t]*$"
)


def fail(msg):
    print("generate-metro-files: FAIL — " + msg, file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------- rendering

def js_num(n):
    """JSON number -> JS literal, preserving the int/float distinction the
    worksheet encodes (41 stays 41; 41.0 stays 41.0)."""
    return repr(n) if isinstance(n, float) else str(n)


def js_str(s):
    return json.dumps(s, ensure_ascii=False)


def iso_date(human):
    """"August 3, 2026" -> "2026-08-03".

    schema.org's dateModified wants ISO 8601; the worksheet carries the date in
    the form the footer prints to a reader. Deriving one from the other keeps
    ONE key rather than adding a second that can disagree with the first — the
    failure this file exists to prevent. A date it cannot parse fails the build
    rather than emitting an invalid one, because a malformed dateModified is a
    field Google ignores silently.
    """
    try:
        return datetime.datetime.strptime(human, "%B %d, %Y").strftime("%Y-%m-%d")
    except ValueError:
        fail('verified_date %r is not "Month D, YYYY", so no ISO dateModified '
             "can be derived from it" % human)


def bbox_js(b, order):
    return "{ " + ", ".join("%s: %s" % (k, js_num(b[k])) for k in order) + " }"


def keyed_lines(groups, indent):
    """Grouped key lists -> one line per group, comma-joined."""
    lines = []
    for gi, group in enumerate(groups):
        line = indent + ", ".join(js_str(k) for k in group)
        if gi != len(groups) - 1:
            line += ","
        lines.append(line)
    return lines


def render_metro_config(w):
    L = []
    a = L.append

    def stmt(code, comment=None, pad=37):
        a("  " + (code.ljust(pad) + " // " + comment if comment else code))

    a("  /* Everything metro-specific that the shared ENGINE blocks below reference")
    a("   * lives here, so an ENGINE block never needs a per-city edit. Fenced ENGINE")
    a("   * blocks are byte-identical across every metro fork — see")
    a("   * docs/ENGINE_SYNC.md and scripts/check_engine_parity.py. */")
    stmt("var THIS_METRO = %s;" % js_str(w["this_metro"]), "key into METRO_EXPLORERS below")
    stmt("var METRO_NAME = %s;" % js_str(w["metro_name"]), "used in user-facing strings")
    a("  var METRO_BBOX = %s;" % bbox_js(w["metro_bbox"], ["minLng", "minLat", "maxLng", "maxLat"]))
    a("  var METRO_CENTER = [%s, %s];" % tuple(js_num(v) for v in w["metro_center"]))
    a("  // Permalink sanity gate: the *greater* metro area (wider than METRO_BBOX).")
    a("  var PERMALINK_GATE = %s;" % bbox_js(w["permalink_gate"], ["minLat", "maxLat", "minLng", "maxLng"]))
    # Emitted ONLY when the worksheet declares it. A fork whose layers are all
    # city-scoped keeps a byte-identical metro-config region, which is what
    # makes this safe to ship through the engine release: the bump workflow
    # applies the release and copies the shared scripts but never regenerates,
    # so a generator that emitted a new line unconditionally would fail every
    # sibling's drift gate. (Both halves of that were learned the hard way —
    # v1.0.16 made the key required and broke worksheet validation; a
    # default-and-always-emit fix then broke the drift gate instead. The rule
    # is stronger than "default to the old value": a fork that has not opted in
    # must see NO change at all.) See docs/ENGINE_SYNC.md.
    if "poi_geocode_bbox" in w:
        a("  // Envelope the POI (office-address) geocoder is bounded to. It tracks the")
        a("  // reach of the fork's WIDEST layer, not the metro: a card that can name an")
        a("  // address outside METRO_BBOX needs that address to be geocodable, and a")
        a("  // bound tighter than the data silently drops those pins no matter how")
        a("  // clean the address is. Set from the worksheet's poi_geocode_bbox — widen")
        a("  // it there whenever a layer's cards start naming farther-away offices.")
        a("  var POI_GEOCODE_BBOX = %s;" % bbox_js(w["poi_geocode_bbox"], ["minLng", "minLat", "maxLng", "maxLat"]))
    a("  var SOCRATA_HOST = %s;" % js_str(w["socrata_host"]))
    a("  // Socrata app token: some metros' portals throttle anonymous requests. It is")
    a("  // a throttling identifier, not a secret — public exposure is Socrata's")
    a("  // intended use (do NOT put an API Key *secret* here). Blank = sent as-is.")
    a("  var SOCRATA_APP_TOKEN = %s;" % js_str(w["socrata_app_token"]))
    a("  var REPO_ISSUES = %s;" % js_str(w["repo_issues"]))
    a("  var FEEDBACK_SUBJECT = %s;" % js_str(w["feedback_subject"]))
    # The words in the search box. Emitted ONLY when the worksheet opts in, the
    # same inertness rule poi_geocode_bbox and brand follow, so an instance
    # without the key sees a byte-identical region — and the shared toolbar's
    # own neutral default stands. The engine reads it through a typeof guard.
    if w.get("geocoder", {}).get("search_placeholder"):
        a("  var SEARCH_PLACEHOLDER = %s;"
          % js_str(w["geocoder"]["search_placeholder"]))
    # Brand-as-data (docs/DEV_PROCESS_ASSESSMENT.md, R1). Same inertness rule as
    # poi_geocode_bbox above: emitted ONLY when the worksheet opts in, so a fork
    # without the key sees a byte-identical region. Engine code may read this
    # only through a typeof guard — a fork without the key has no METRO_BRAND
    # and must keep its historical composed strings.
    if "brand" in w:
        b = w["brand"]
        fields = ["appName: %s" % js_str(b["app_name"])]
        if "product_name" in b:
            fields.append("productName: %s" % js_str(b["product_name"]))
        if "instance_tag" in b:
            fields.append("instanceTag: %s" % js_str(b["instance_tag"]))
        a("  // Brand identity as worksheet data — never read from an ENGINE block")
        a("  // without a typeof guard (forks that have not opted in do not define it).")
        a("  var METRO_BRAND = { %s };" % ", ".join(fields))
    # The words on the coverage key. Same inertness rule as brand and
    # poi_geocode_bbox above: emitted ONLY when the worksheet opts in, so an
    # instance without the key sees a byte-identical region and simply draws the
    # wash with no legend, exactly as before the key existed. The engine reads it
    # through a typeof guard for that reason. The BANDS are engine and the same
    # everywhere; what a reader calls them is not, and it is not derivable —
    # Chicago's METRO_NAME is "Chicago" while its coverage is 89 Illinois
    # counties, so a generated "Outside " + METRO_NAME would be plainly wrong.
    if "coverage_key" in w:
        ck = w["coverage_key"]
        fields = ["outside: %s" % js_str(ck["outside"])]
        if "region" in ck:
            r = ck["region"]
            rf = ["edge: %s" % js_str(r["edge"]), "label: %s" % js_str(r["label"])]
            if "sub" in r:
                rf.append("sub: %s" % js_str(r["sub"]))
            fields.append("region: { %s }" % ", ".join(rf))
        a("  // Names for the bands of the out-of-scope wash (ENGINE scope-mask builds")
        a("  // the key from these). `region` is the MIDDLE band and is present only for")
        a("  // an instance whose full coverage is a proper subset of a wider region its")
        a("  // statewide layers still answer in; it also requires that instance's boot")
        a("  // to hand drawOutOfScopeMask() the region geometry, because the key names")
        a("  // only the bands that were actually drawn.")
        a("  var COVERAGE_KEY = { %s };" % ", ".join(fields))
    a("  /* Sibling District Explorer deployments — one canonical list shared by every")
    a("   * metro fork. When a new metro launches, add its entry to every fork's")
    a("   * worksheet and regenerate (Conversion 3 will source this list from the")
    a("   * fleet manifest instead). THIS_METRO drops the fork's own entry so the")
    a("   * list is identical in every fork. `bbox` (greater metro area, mirroring")
    a("   * that fork's PERMALINK_GATE) and `emoji` feed the sibling-metro portal")
    a("   * easter egg (ENGINE metro-portal): wander the map into a sibling's bbox —")
    a("   * or search/geolocate a point inside one — and the app offers to hand you")
    a("   * off to that fork's explorer. */")
    a("  var METRO_EXPLORERS = [")
    for i, e in enumerate(w["metro_explorers"]):
        tail = "," if i != len(w["metro_explorers"]) - 1 else ""
        head = "    { id: %s, label: %s, url: %s, emoji: %s," % (
            js_str(e["id"]), js_str(e["label"]), js_str(e["url"]), js_str(e["emoji"]))
        # A rebranded sibling names its app outright; absent, the engine keeps
        # composing label + " District Explorer" as it always has.
        if "explorer_name" in e:
            head += " explorerName: %s," % js_str(e["explorer_name"])
        if "bbox" in e:
            a(head)
            a("      bbox: %s }%s" % (bbox_js(e["bbox"], ["minLng", "minLat", "maxLng", "maxLat"]), tail))
        else:
            a(head.rstrip(",") + " }%s" % tail)
    a("  ];")
    a("  // FALLBACK district-number key list, fed through extractDistrictNumber")
    a("  // (which adds a name-field regex fallback for the layers whose number only")
    a("  // lives inside a \"…name\" string). The factories declare per-layer hoverName")
    a("  // sourced from the same properties each click card reads (the hover-parity")
    a("  // rule), so this generic path only runs if hoverName comes back empty. These")
    a("  // keys are this metro's dataset vocabulary — re-seed them from observed")
    a("  // field names in the worksheet, keeping encoded fields out.")
    a("  var HOVER_NUMBER_KEYS = [")
    L.extend(keyed_lines(w["hover_number_keys"], "    "))
    a("  ];")
    a("")
    a("  // Name-ish property keys that read better than a bare district number when a")
    a("  // feature carries one — deliberately narrow. Generic \"name\"/\"label\" fields")
    a("  // are excluded on purpose: for legislative layers those just restate the")
    a("  // number this pairs with.")
    a("  var HOVER_NAME_KEYS = [")
    L.extend(keyed_lines(w["hover_name_keys"], "    "))
    a("  ];")
    return "\n".join(L)


def render_layer_area_rank(w):
    layers = sorted(w["layers"], key=lambda l: l["area_rank"])
    L = []
    a = L.append
    a("  // Approximate real-world area ranking, largest to smallest, used to keep")
    a("  // smaller/more granular boundaries visible on top of larger ones (see")
    a("  // reorderActiveLayers()). Hand-authored from known geography — there's no")
    a("  // geometry library in this codebase to compute polygon area from data.")
    a("  // GENERATED from the worksheet's layers[] (area_rank order + rank notes).")
    a("  var LAYER_AREA_RANK = [")
    for i, l in enumerate(layers):
        for c in l.get("rank_comment", []):
            a("    // " + c)
        entry = js_str(l["id"]) + ("," if i != len(layers) - 1 else "")
        note = l.get("rank_note")
        a(("    " + entry.ljust(20) + (" // " + note if note else "")).rstrip())
    a("  ];")
    return "\n".join(L)


def render_sw_metro_config(w):
    L = []
    a = L.append
    a("const CACHE_NAME = %s;" % js_str(w["sw"]["cache_name"]))
    a("")
    a("const SHELL_URLS = [")
    for u in w["sw"]["shell_urls"]:
        a("  %s," % js_str(u))
    a("];")
    a("")
    a("// Boundary geometry (data/app/*.json, fetched lazily on first toggle).")
    a("// Boundaries change ~once a decade, so serve them cache-first (instant, and")
    a("// works offline) and refresh in the background. Precached at install so")
    a("// those layers work offline.")
    a("const GEOMETRY_URLS = [")
    for g in w["data_files"]["geometry"]:
        a("  %s," % js_str("./data/app/" + g["file"]))
    a("];")
    a("")
    a("// Roster/officeholder data (also in data/app/) is refreshed by the weekly CI")
    a("// and must never be served stale — network-first, with the cached copy only")
    a("// as an offline fallback. Same freshness rule as the shell.")
    a("const ROSTER_URLS = [")
    for r in w["data_files"]["rosters"]:
        a("  %s," % js_str("./data/app/" + r["file"]))
    a("];")
    return "\n".join(L)


def render_validator_config(w):
    L = []
    a = L.append
    a("# Floor, not a moving target: new layers only raise this; a drop means")
    a("# modules were lost.")
    a("MIN_REGISTER_LAYER = %d" % w["min_register_layer"])
    a("")
    a("# Every layer id that must be registered in index.html. Most modules register")
    a("# through the factories, so deleting one would NOT lower the raw registerLayer(")
    a("# count above — this per-id list is the direct module-loss guard. Emitted in")
    a("# LAYER_AREA_RANK order; check 5 keeps the two naming the same set.")
    a("EXPECT_LAYER_IDS = [")
    line = "   "
    for l in sorted(w["layers"], key=lambda x: x["area_rank"]):
        piece = " %s," % js_str(l["id"])
        if len(line) + len(piece) > 78:
            a(line)
            line = "   "
        line += piece
    a(line)
    a("]")
    a("")
    a("# file -> (min features, max features) for the boundary layers fetched by the app.")
    a("GEOMETRY_FILES = {")
    for g in w["data_files"]["geometry"]:
        a("    %s: (%d, %d),%s" % (js_str(g["file"]), g["min_features"], g["max_features"],
                                   ("  # " + g["note"]) if g.get("note") else ""))
    a("}")
    a("")
    a("# file -> minimum key count (officeholder rosters).")
    a("ROSTER_FILES = {")
    for r in w["data_files"]["rosters"]:
        a("    %s: %d,%s" % (js_str(r["file"]), r["min_keys"],
                             ("  # " + r["note"]) if r.get("note") else ""))
    a("}")
    a("")
    a("# Files the app references DYNAMICALLY — the URL is built from a slug at")
    a("# runtime (the gaps panel's <slug>-county-outline.json contract), so no")
    a("# literal appears in index.html. Exempt from the reference check only;")
    a("# existence, shape and the negative-point test still apply.")
    a("DYNAMIC_REFERENCE = frozenset({")
    for g in w["data_files"]["geometry"]:
        if g.get("dynamic_reference"):
            a("    %s," % js_str(g["file"]))
    for r in w["data_files"]["rosters"]:
        if r.get("dynamic_reference"):
            a("    %s," % js_str(r["file"]))
    a("})")
    return "\n".join(L)


def render_smoke_config(w):
    pt = w["anchor_point"]
    neg = w["negative_point"]
    L = []
    a = L.append
    a("const POINT = \"%.5f,%.5f\";%s" % (pt["lat"], pt["lng"],
                                          (" // " + pt["note"]) if pt.get("note") else ""))
    a("const OFFLINE = [%s];" % ", ".join(js_str(x["layer"]) for x in w["anchors"]))
    a("const EXPECT_DISTRICT = { %s };" % ", ".join(
        "%s: %s" % (js_str(x["layer"]), js_str(x["expected"])) for x in w["anchors"]))
    a("const NEGATIVE_POINT = \"%.5f,%.5f\";%s" % (neg["lat"], neg["lng"],
                                                   (" // " + neg["note"]) if neg.get("note") else ""))
    # The app's own display name, so a behaviour check can assert the brand
    # without hardcoding it. SF's smoke test carried
    # /San Francisco District Explorer/ as a literal and FAILED THE REBRAND —
    # a correct rename breaking a gate, which is the failure mode a gate must
    # not have (landing_test.mjs learned the same lesson from a hardcoded
    # (il|nyc|sf) tag list). Derived the same way appDisplayName() derives it at
    # runtime, so the two cannot disagree.
    a("const APP_NAME = %s;" % js_str(
        (w.get("brand") or {}).get("app_name") or (w["metro_name"] + " District Explorer")))
    a("const EXPECT_LAYERS = %d;%s" % (len(w["layers"]),
                                       (" // " + w["layer_count_note"]) if w.get("layer_count_note") else ""))
    return "\n".join(L)


def render_metro_facts(w):
    groups = {}
    for l in w["layers"]:
        groups[l["group"]] = groups.get(l["group"], 0) + 1
    anchor = w["anchor_point"]
    neg = w["negative_point"]
    L = []
    a = L.append
    a("**Metro facts** (generated from `metro-worksheet.json` — edit the worksheet and run")
    a("`python3 scripts/generate_metro_files.py`; hand-edits here fail CI):")
    a("")
    a("- Metro: %s (`%s`) — %s" % (w["metro_name"], w["this_metro"], w["domains"]["canonical"]))
    a("- Geocoders: address %s; unbounded %s; POI %s" % (
        w["geocoder"]["address"], w["geocoder"]["unbounded"], w["geocoder"]["poi"]))
    a("- Ground truth: %.5f,%.5f (%s) → %s. Negative point %.5f,%.5f (%s)." % (
        anchor["lat"], anchor["lng"], anchor.get("note", ""),
        "; ".join("%s %s" % (x["layer"], x["expected"]) for x in w["anchors"]),
        neg["lat"], neg["lng"], neg.get("note", "")))
    a("- Layers: %d registered (%s); `registerLayer(` floor %d. Debug namespace `window.%s`." % (
        len(w["layers"]),
        ", ".join("%s %d" % (g, groups[g]) for g in ["political", "safety", "schools", "geography"] if g in groups),
        w["min_register_layer"], w["exports_name"]))
    a("- Scheduled workflows: %s." % "; ".join(
        "`%s` (%s)" % (wf["file"], wf["schedule"]) for wf in w["workflows"]))
    a("- Source registry: %s" % (
        "`%s` (machine-checked monthly)" % w["data_sources"]["registry"]
        if isinstance(w["data_sources"], dict) else "%d rows in the worksheet" % len(w["data_sources"])))
    return "\n".join(L)


def render_metro_header(w, repo_front=False):
    """The README's title and one-line pitch.

    This reads the BRAND, not metro_name. All six READMEs still said
    "<Metro> District Explorer" — the product name the fleet retired at the
    rebrand — because the rebrand reached every surface a reader LOADS and
    missed the one a reader LANDS ON from GitHub. metro_name is not the fix
    either: Illinois's is still "Chicago", a true record of where the app
    started, which is the same trap build_history_page.py documents for its
    own title.

    Illinois's README target is the REPOSITORY's own front page rather than an
    instance folder's (INSTANCES gives it docs: "."), and that page introduces
    six instances two paragraphs down — so it takes the product name, where an
    instance README names its own instance. A fork carrying no brand block
    still sees the byte-identical file it always had.
    """
    b = w.get("brand")
    if not b:
        return "\n".join([
            "# %s District Explorer" % w["metro_name"],
            "",
            "**Click any point in %s — or search an address — and see every civic district that contains it, and who represents you there.**" % w["metro_name"],
        ])
    name = (b.get("product_name") or b["app_name"]) if repo_front else b["app_name"]
    return "\n".join([
        "# %s" % name,
        "",
        "**%s**" % b["tagline"],
    ])


# ------------------------------------------------------ the public sources page

def html_esc(s):
    """Escape for HTML text and double-quoted attribute values alike."""
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def render_perf_config(w):
    """The two smoke-config lines the performance harness shares: the anchor
    point and the no-API offline layer list. perf_profile.mjs hand-mirrored
    these from smoke_test.mjs until the 2026-08-24 scripts audit — the exact
    drift this generator exists to end."""
    pt = w["anchor_point"]
    return "\n".join([
        "const POINT = \"%.5f,%.5f\";%s" % (
            pt["lat"], pt["lng"], (" // " + pt["note"]) if pt.get("note") else ""),
        "const OFFLINE = [%s];" % ", ".join(js_str(x["layer"]) for x in w["anchors"]),
    ])


def render_verified_date(w):
    """The footer's date, SERVER-RENDERED into the element rather than assigned
    to it at boot.

    It used to be one line of JavaScript writing into an empty
    <strong id="verified-date">, which meant the raw HTML of all six instances
    carried no date at all — measured 2026-09-11, every one of them shipped the
    element empty. A crawler that does not execute JavaScript therefore saw a
    page making no freshness claim, on a tool whose entire value is who holds a
    seat NOW. sources.html had been server-rendering the same worksheet key
    since it shipped, so the pattern was already here; index.html was the
    surface that never got it.
    """
    return ('          <strong id="verified-date">%s</strong>'
            % html_esc(w["verified_date"]))


# ------------------------------------------------------------- brand-as-data
# (docs/DEV_PROCESS_ASSESSMENT.md, stage R1.) Every renderer below reproduces a
# surface that was hand-written until the brand key existed; the values moved
# into the worksheet verbatim, so opting in changes no rendered byte until the
# worksheet's brand values themselves change.

def render_head_analytics(w):
    ga = w["brand"]["analytics"]
    return "\n".join([
        "<!-- Google tag (gtag.js) — production host only; keeps local dev + CI out of analytics -->",
        "<script>",
        "  (function () {",
        "    if (location.hostname !== '%s') return;" % ga["ga_hostname"],
        "    if (window.top !== window.self) return; // top-level only — no Google Analytics inside an embedded iframe (the cookieless GoatCounter still counts)",
        "    var s = document.createElement('script');",
        "    s.async = true;",
        "    s.src = 'https://www.googletagmanager.com/gtag/js?id=%s';" % ga["ga_id"],
        "    document.head.appendChild(s);",
        "    window.dataLayer = window.dataLayer || [];",
        "    window.gtag = function () { dataLayer.push(arguments); };",
        "    gtag('js', new Date());",
        "    gtag('config', '%s');" % ga["ga_id"],
        "  })();",
        "</script>",
    ])


def render_head_brand(w):
    b = w["brand"]
    h = b["head"]
    canonical = w["domains"]["canonical"]
    og_image = canonical + "og-image.png"
    e = html_esc
    return "\n".join([
        "<title>%s</title>" % e(h["title"]),
        '<meta name="description" content="%s" />' % e(h["description"]),
        '<meta name="robots" content="index, follow" />',
        '<link rel="canonical" href="%s" />' % e(canonical),
        "",
        "<!-- Open Graph / social share previews (Facebook, LinkedIn, iMessage, Slack…) -->",
        '<meta property="og:type" content="website" />',
        '<meta property="og:site_name" content="%s" />' % e(b["app_name"]),
        '<meta property="og:title" content="%s" />' % e(h["og_title"]),
        '<meta property="og:description" content="%s" />' % e(h["og_description"]),
        '<meta property="og:url" content="%s" />' % e(canonical),
        '<meta property="og:image" content="%s" />' % e(og_image),
        '<meta property="og:image:width" content="1200" />',
        '<meta property="og:image:height" content="630" />',
        '<meta property="og:image:alt" content="%s" />' % e(h["og_image_alt"]),
        '<meta property="og:locale" content="en_US" />',
        "",
        "<!-- Twitter / X card -->",
        '<meta name="twitter:card" content="summary_large_image" />',
        '<meta name="twitter:title" content="%s" />' % e(h["twitter_title"]),
        '<meta name="twitter:description" content="%s" />' % e(h["twitter_description"]),
        '<meta name="twitter:image" content="%s" />' % e(og_image),
    ])


def render_head_theme(w):
    b = w["brand"]
    L = [
        '<meta name="theme-color" content="%s">' % b["theme_color"],
        "",
        '<link rel="icon" type="image/svg+xml" href="%s" />' % html_esc(b["favicon_data_uri"]),
    ]
    # iOS does NOT read the web app manifest's icons when adding to the Home
    # Screen — it reads this tag and nothing else, which is why an iPhone
    # install had no branded icon at all while Android's was merely stale. The
    # companion title tag matters for the same reason: absent it, iOS labels
    # the shortcut from <title>, and <title> is the question-led SEO string
    # ("What district am I in? Illinois — districtry"), which truncates to a
    # fragment of a question under the icon.
    if b.get("apple_touch_icon"):
        L += [
            "",
            '<link rel="apple-touch-icon" href="%s" />' % html_esc(b["apple_touch_icon"]),
            '<meta name="apple-mobile-web-app-title" content="%s" />'
            % html_esc(b.get("product_name") or b["app_name"]),
        ]
    return "\n".join(L)


def render_brand_palette(w):
    """The :root accent tokens in index.html — the four values the worksheet's
    palette key already carried while the stylesheet restated them by hand (two
    copies of one fact, the drift class this generator exists to end)."""
    p = w["palette"]
    notes = p.get("notes", {})
    L = []
    if p.get("label"):
        L.append("    /* ---- %s ---- */" % p["label"])
    for key, prop in [("accent", "--accent"), ("accent_deep", "--accent-deep"),
                      ("accent_warm", "--accent-warm"),
                      ("accent_warm_deep", "--accent-warm-deep")]:
        line = "    %s: %s;" % (prop, p[key])
        if notes.get(key):
            line += " /* %s */" % notes[key]
        L.append(line)
    return "\n".join(L)


def render_masthead_brand(w):
    """The masthead wordmark and subtitle.

    When the worksheet carries product_name + instance_tag the wordmark is the
    BRAND form — one indivisible lowercase word plus the instance tag, the tag
    being a control that opens the fleet switcher ("districtry / il"). Without
    those two keys it stays the historical single title-text span, which is what
    keeps a fork that has not rebranded byte-identical here: SF and NYC carry no
    brand block at all, so they never reach the first branch.
    """
    b = w["brand"]
    e = html_esc
    if b.get("product_name") and b.get("instance_tag"):
        # The product name LINKS HOME. On a fleet site the wordmark is the way
        # back to the front door, and a reader who arrived on an instance has
        # no other route to the list of places. "../" rather than "/" so the
        # link is correct however the instance is mounted.
        wordmark = (
            '        <span class="title-text"><a class="dst-wordmark-link" href="../">%s</a>'
            ' <span class="dst-metro-switch">'
            '<button type="button" class="title-metro dst-metro-btn" aria-expanded="false" '
            'aria-haspopup="true" aria-label="%s — switch explorer">/ %s'
            '<span class="dst-metro-caret" aria-hidden="true">&#9662;</span></button>'
            '<span class="dst-metro-menu" role="menu"></span></span></span>'
            % (e(b["product_name"]), e(b["app_name"]), e(b["instance_tag"]))
        )
    else:
        wordmark = '        <span class="title-text">%s</span>' % e(b["app_name"])
    # THE TAGLINE IS THE HEADING, not the wordmark. The hub's <h1> used to wrap
    # the wordmark and the metro switcher, so the page's one heading resolved to
    # the brand plus a navigation control — measured 90 characters of that on
    # Illinois, with nothing in it about districts. Every sub-page already put
    # the topic in the same class. Nothing moves on screen: the element that was
    # a <small> is now the <h1>, styled by the same rules.
    return "\n".join([
        wordmark,
        "      </span>",
        '      <h1 class="title-tagline">%s</h1>' % e(b["tagline"]),
    ])


def render_goatcounter(w):
    return "\n".join([
        '<script data-goatcounter="%s"' % html_esc(w["brand"]["analytics"]["goatcounter_url"]),
        '        async src="//gc.zgo.at/count.js"></script>',
    ])


def render_sources_palette(w):
    """The sources page's mirrored :root accents — the page is deliberately
    standalone (no shared stylesheet), so it restates the tokens; this region
    is what keeps the restatement from drifting."""
    p = w["palette"]
    return "\n".join([
        "  --accent: %s;" % p["accent"],
        "  --accent-deep: %s;" % p["accent_deep"],
        "  --accent-warm: %s;" % p["accent_warm"],
    ])


def render_sources_verified(w):
    return ('        <p class="verified">Data last verified: <strong>%s</strong></p>'
            % html_esc(w["verified_date"]))


def render_source_credits(w):
    """The upstream publishers the app credits as a whole — the list that was
    the footer's source row before this page existed."""
    L = []
    a = L.append
    a('      <ul class="credit-list">')
    for c in w["sources_page"]["credits"]:
        a('        <li>')
        a('          <a href="%s" target="_blank" rel="noopener">%s</a>'
          % (html_esc(c["url"]), html_esc(c["label"])))
        if c.get("note"):
            a('          <span class="credit-note">%s</span>' % html_esc(c["note"]))
        a('        </li>')
    a('      </ul>')
    return "\n".join(L)


# Group id -> (heading, one-line orientation). The four groups are the layer
# registry's own `group` values, so the page can never grow a fifth section the
# app doesn't have.
GROUP_HEADINGS = [
    ("political", "Political &amp; legislative",
     "Districts that elect somebody — from your ward to your seat in Congress."),
    ("safety", "Public safety",
     "Who answers a call at this address, and where they answer it from."),
    ("schools", "Schools",
     "The district, the attendance zone, and the schools nearest the point."),
    ("geography", "Geography &amp; amenities",
     "The boundaries that place an address without electing anyone, plus the nearest public services."),
]

MATRIX_COLUMNS = ["Layer", "What it answers", "Boundary source", "Who it names", "Where it applies"]


def render_jsonld_graph(w):
    """index.html's whole ld+json graph, from the worksheet.

    IT WAS HAND-WRITTEN SIX TIMES, and that is the shape of Michigan's go-live
    bug: mi/sources.html shipped IOWA's entire identity block — canonical,
    og:url, title and the whole graph — because the page was cloned and only
    its GENERATED regions were ever regenerated. page_consistency_test.mjs
    gates that now for all 32 sitemap pages, so this is not re-fixing it; the
    reason to generate THIS graph is that nothing could add a field to it
    without adding it six times by hand, which is why it carried no
    dateModified while every page claimed a freshness the graph never stated.

    THE CONSTANTS ARE LITERALS HERE, not worksheet keys. Nine fields were
    identical across all six instances on 2026-09-11 — the publisher, the free
    Offer, the browser requirements, operatingSystem, inLanguage, sameAs,
    applicationCategory, isAccessibleForFree. Six hand-written copies were six
    chances for one to drift; one literal is none.

    EVERYTHING DERIVABLE IS DERIVED: @id, url, image, isPartOf and publisher
    from the instance tag, name from brand.app_name. What remains in the
    worksheet is the four values that are genuinely this instance's own prose.

    dateModified comes from verified_date — the same key the footer and
    sources.html already print, so the date a reader sees and the date a
    crawler reads cannot disagree.
    """
    b = w["brand"]
    g = b.get("jsonld")
    if not g:
        return ""
    tag = b["instance_tag"]
    base = "https://districtry.com/%s/" % tag
    SITE = "https://districtry.com/"
    name = b["app_name"]

    area = g["area_served"]
    if area.get("city"):
        area_node = ('{ "@type": "City", "name": %s, "containedInPlace": '
                     '{ "@type": "State", "name": %s } }'
                     % (js_str(area["city"]), js_str(area["state"])))
    else:
        area_node = '{ "@type": "State", "name": %s }' % js_str(area["state"])

    L = []
    a = L.append
    # The element, not just its body. GENERATED markers are HTML comments and
    # an HTML comment INSIDE a ld+json script makes the JSON unparseable —
    # silently, because a crawler drops the graph without reporting anything.
    a('<script type="application/ld+json">')
    a('{')
    a('  "@context": "https://schema.org",')
    a('  "@graph": [')
    a('    {')
    a('      "@type": "WebSite",')
    a('      "@id": "%s#website",' % base)
    a('      "url": "%s",' % base)
    a('      "name": %s,' % js_str(name))
    a('      "description": %s,' % js_str(g["site_description"]))
    a('      "inLanguage": "en-US",')
    a('      "publisher": { "@id": "%s#publisher" }' % SITE)
    a('    },')
    a('    {')
    # ONE PUBLISHER FOR THE SITE, not one per instance. Six instances each
    # minting their own #publisher described one organisation as seven, so
    # nothing tied districtry Illinois's publisher to districtry Iowa's. The
    # node stays INLINE on every page — a crawler reading one page cannot
    # resolve an @id defined in another document — but the identifier is the
    # same everywhere, which is what makes them one entity. The root path is
    # what page_consistency_test.mjs allows as pointing UP rather than
    # sideways into a sibling.
    a('      "@type": "Organization",')
    a('      "@id": "%s#publisher",' % SITE)
    a('      "name": "Overberg",')
    a('      "url": "https://overberg.co"')
    a('    },')
    a('    {')
    # THE PERSON IS A NODE, not a string. This is civic data about who holds
    # public office, which Google's quality guidelines hold to their highest
    # bar, and the graph ran WebSite -> Organization and stopped — no author
    # anywhere on the site, measured across all 33 content pages on
    # 2026-09-11. A named author with a URL is the cheapest part of that bar
    # and the site had none of it.
    a('      "@type": "Person",')
    a('      "@id": "%s#author",' % SITE)
    a('      "name": "Adam Overberg",')
    a('      "url": "https://overberg.co",')
    # A contactable author, not just a named one. The quality guidelines ask how a reader reaches whoever stands behind the page, and a name plus a URL answers half of it.
    a('      "email": "hello@overberg.co",')
    a('      "worksFor": { "@id": "%s#publisher" }' % SITE)
    a('    },')
    a('    {')
    a('      "@type": "WebApplication",')
    a('      "name": %s,' % js_str(name))
    a('      "url": "%s",' % base)
    a('      "description": %s,' % js_str(g["app_description"]))
    a('      "applicationCategory": "Reference",')
    a('      "operatingSystem": "Any (modern web browser)",')
    a('      "browserRequirements": "Requires JavaScript",')
    a('      "isAccessibleForFree": true,')
    a('      "offers": { "@type": "Offer", "price": "0", "priceCurrency": "USD" },')
    a('      "inLanguage": "en-US",')
    a('      "image": "%sog-image.png",' % base)
    a('      "areaServed": %s,' % area_node)
    a('      "keywords": %s,' % js_str(g["keywords"]))
    a('      "author": { "@id": "%s#author" },' % SITE)
    a('      "isPartOf": { "@id": "%s#website" },' % base)
    # The one field this whole change exists to make possible. ISO 8601, from
    # the same key the footer prints in prose.
    a('      "dateModified": %s,' % js_str(iso_date(w["verified_date"])))
    a('      "sameAs": "https://github.com/ThursdaysFamous/districtry"')
    a('    }')
    a('  ]')
    a('}')
    a('</script>')
    return "\n".join(L)


def render_guide_links(w):
    """The app footer's links to this instance's own explainer pages.

    THE SAME worksheet key that links the sources.html matrix row. Measured
    2026-09-11: not one instance hub linked any of the six explainer pages, and
    not one sources page did either — they were reachable only through
    faq.html, so a reader on the map had no route to the page written to answer
    the question they were asking. Two surfaces, one key, because a hand-kept
    list in six index.html files is a list that goes stale the next time an
    explainer ships.

    Emits nothing when no layer declares a guide, so an instance that has no
    explainer pages sees a byte-identical footer.
    """
    guides = [l["guide"] for l in sorted(w["layers"], key=lambda x: x["area_rank"])
              if l.get("guide")]
    if not guides:
        return ""
    return "\n".join(
        '        <a href="%s">%s</a>' % (html_esc(g["href"]), html_esc(g["text"]))
        for g in guides)


def render_layer_matrix(w):
    """Every registered layer, grouped, with the provenance of each.

    Generated from the SAME layers[] list that drives EXPECT_LAYER_IDS and the
    smoke test's layer count, which is the point: a layer cannot ship without a
    row here, and a row here cannot outlive its layer.
    """
    by_group = {}
    for l in sorted(w["layers"], key=lambda x: x["area_rank"]):
        by_group.setdefault(l["group"], []).append(l)
    unknown = set(by_group) - {g for g, _, _ in GROUP_HEADINGS}
    if unknown:
        fail("layers use group(s) the sources page has no section for: %s"
             % ", ".join(sorted(unknown)))

    L = []
    a = L.append
    a('      <p class="matrix-lede">%d layers — %s. Each row names the publisher '
      'the boundary comes from, where the names on the card come from, and the '
      'ground the layer actually answers on — outside that ground the layer '
      'hides itself rather than guessing.</p>'
      % (len(w["layers"]),
         ", ".join("%d %s" % (len(by_group[g]), t.lower().replace("&amp;", "and"))
                   for g, t, _ in GROUP_HEADINGS if g in by_group)))
    a('      <nav class="matrix-nav" aria-label="Jump to a layer group">')
    for gid, title, _ in GROUP_HEADINGS:
        if gid in by_group:
            a('        <a href="#%s">%s</a>' % (gid, title))
    a('      </nav>')

    for gid, title, blurb in GROUP_HEADINGS:
        if gid not in by_group:
            continue
        rows = by_group[gid]
        a('')
        a('      <section class="matrix-group" id="%s">' % gid)
        a('        <h2>%s <span class="matrix-count">%d layer%s</span></h2>'
          % (title, len(rows), "" if len(rows) == 1 else "s"))
        a('        <p class="matrix-blurb">%s</p>' % blurb)
        a('        <div class="matrix-wrap">')
        a('          <table class="matrix">')
        a('            <thead>')
        a('              <tr>%s</tr>'
          % "".join('<th scope="col">%s</th>' % html_esc(c) for c in MATRIX_COLUMNS))
        a('            </thead>')
        a('            <tbody>')
        for l in rows:
            src = l.get("source")
            if not src:
                fail('layer %r has no source block — a fork that sets sources_page '
                     'must give every layer one (see the schema)' % l["id"])
            a('              <tr id="layer-%s">' % l["id"])
            th = ('<span class="layer-name">%s</span><code>%s</code>'
                  % (html_esc(l["label"]), html_esc(l["id"])))
            # A layer that has its own explainer page links to it from the row
            # that already describes the layer. This is the only place on the
            # site where every layer is enumerated, so it is where a link per
            # concept costs nothing to keep current: the href and the anchor
            # text come from the worksheet, beside the layer they describe.
            guide = l.get("guide")
            if guide:
                th += ('<a class="layer-guide" href="%s">%s</a>'
                       % (html_esc(guide["href"]), html_esc(guide["text"])))
            a('                <th scope="row">%s</th>' % th)
            a('                <td data-label="%s">%s</td>'
              % (MATRIX_COLUMNS[1], html_esc(src["answers"])))
            a('                <td data-label="%s">' % MATRIX_COLUMNS[2])
            a('                  <ul class="src-list">')
            for b in src["boundary"]:
                if b.get("url"):
                    a('                    <li><a href="%s" target="_blank" rel="noopener">%s</a></li>'
                      % (html_esc(b["url"]), html_esc(b["label"])))
                else:
                    a('                    <li>%s</li>' % html_esc(b["label"]))
            a('                  </ul>')
            a('                </td>')
            a('                <td data-label="%s">%s</td>'
              % (MATRIX_COLUMNS[3],
                 html_esc(src["people"]) if src.get("people") else '<span class="matrix-none">—</span>'))
            a('                <td data-label="%s">%s</td>'
              % (MATRIX_COLUMNS[4],
                 html_esc(src["applies"]) if src.get("applies") else '<span class="matrix-none">—</span>'))
            a('              </tr>')
        a('            </tbody>')
        a('          </table>')
        a('        </div>')
        a('      </section>')
    return "\n".join(L)


# Regions every fork has. Optional regions are appended by targets_for() only
# when the worksheet opts in, so a fork that has not sees a byte-identical file
# and an untouched CI gate (docs/ENGINE_SYNC.md, "a shared-script change must be
# inert in a fork that hasn't opted in").
# Every instance served from this repo, and where its files live.
#
# The three are NOT symmetric and this table is where that is stated rather
# than hidden. `il` predates the consolidation, so its app sits in il/ while its
# tooling and its worksheet are still at the repo root; sf and nyc arrived as
# whole forks, so each keeps everything under its own folder. Making them
# uniform (il's instance-specific scripts and worksheet moving into il/) is a
# mechanical follow-up, not a prerequisite — a three-row table costs less than
# a special case scattered through the renderers.
#
#   app       the instance's own directory (index.html, sw.js, sources.html)
#   scripts   where ITS validate_index.py / smoke_test.mjs / perf harness live
#   docs      where ITS CLAUDE.md and README.md live
#   worksheet the file that drives all of it
INSTANCES = {
    "il":  {"app": "il",  "scripts": "scripts",     "docs": ".",   "worksheet": "metro-worksheet.json"},
    "ca":  {"app": "ca",  "scripts": "ca/scripts",  "docs": "ca",  "worksheet": "ca/metro-worksheet.json"},
    "ny":  {"app": "ny",  "scripts": "ny/scripts",  "docs": "ny",  "worksheet": "ny/metro-worksheet.json"},
    "wi":  {"app": "wi",  "scripts": "wi/scripts",  "docs": "wi",  "worksheet": "wi/metro-worksheet.json"},
    "ia":  {"app": "ia",  "scripts": "ia/scripts",  "docs": "ia",  "worksheet": "ia/metro-worksheet.json"},
    "mi":  {"app": "mi",  "scripts": "mi/scripts",  "docs": "mi",  "worksheet": "mi/metro-worksheet.json"},
}


def _p(*parts):
    """Join, dropping the "." that `docs: "."` would otherwise leave in front."""
    return "/".join(x for x in parts if x not in (".", ""))


def targets_for(w, inst):
    """Every region this instance generates, as (path, region, renderer).

    Opt-in is keyed on the WORKSHEET, never on "does the file happen to exist":
    a missing file or fence in an instance that DID opt in is a hard failure,
    which is what a silently-skipped region would have hidden.
    """
    app, scr, docs = inst["app"], inst["scripts"], inst["docs"]
    targets = [
        (_p(app, "index.html"), "metro-config", render_metro_config),
        (_p(app, "index.html"), "layer-area-rank", render_layer_area_rank),
        (_p(app, "sw.js"), "sw-metro-config", render_sw_metro_config),
        (_p(scr, "validate_index.py"), "validator-config", render_validator_config),
        (_p(scr, "smoke_test.mjs"), "smoke-config", render_smoke_config),
        (_p(docs, "CLAUDE.md"), "metro-facts", render_metro_facts),
        (_p(docs, "README.md"), "metro-header",
         functools.partial(render_metro_header, repo_front=(docs == "."))),
    ]
    if "verified_date" in w:
        targets.append((_p(app, "index.html"), "verified-date", render_verified_date))
        targets.append((_p(app, "index.html"), "guide-links", render_guide_links))
        targets.append((_p(app, "index.html"), "jsonld-graph", render_jsonld_graph))
    if "perf_profile" in w:
        # Worksheet-relative to the instance's own scripts dir.
        targets.append((_p(scr, os.path.basename(w["perf_profile"]["file"])),
                        "perf-config", render_perf_config))
    if "sources_page" in w:
        page = w["sources_page"]["file"]
        targets.append((page, "sources-verified", render_sources_verified))
        targets.append((page, "source-credits", render_source_credits))
        targets.append((page, "layer-matrix", render_layer_matrix))
    if "brand" in w:
        # THE TWO ANALYTICS SURFACES ARE INDEPENDENTLY OPT-IN, and that is a
        # privacy property rather than a convenience. `analytics` used to be
        # REQUIRED inside a brand block with a ga_id, so adopting the districtry
        # brand would have FORCED Google Analytics onto SF — an app that ships
        # none today and whose readers have never been sent to Google. A rebrand
        # must not add a tracker. So each region is emitted only when the
        # worksheet actually names it, and an instance that wants the brand
        # without the counter simply omits the keys.
        an = w["brand"].get("analytics") or {}
        for region, renderer in (
            ("head-brand", render_head_brand),
            ("head-theme", render_head_theme),
            ("brand-palette", render_brand_palette),
            ("masthead-brand", render_masthead_brand),
        ):
            targets.append((_p(app, "index.html"), region, renderer))
        if an.get("ga_id"):
            targets.append((_p(app, "index.html"), "head-analytics",
                            render_head_analytics))
        if an.get("goatcounter_url"):
            targets.append((_p(app, "index.html"), "goatcounter",
                            render_goatcounter))
        if "sources_page" in w:
            targets.append((w["sources_page"]["file"], "sources-palette",
                            render_sources_palette))
    return targets


# ---------------------------------------------------------------- splicing

FLEET_URL = "https://chidistricts.com/metros.json"


def render_explorers_json(entries):
    """Render a metro_explorers array in the worksheet's two-lines-per-entry
    house style, so a fleet sync rewrites only those lines."""
    L = ["["]
    for i, e in enumerate(entries):
        tail = "," if i != len(entries) - 1 else ""
        head = '    { "id": %s, "label": %s, "url": %s, "emoji": %s,' % (
            json.dumps(e["id"]), json.dumps(e["label"], ensure_ascii=False),
            json.dumps(e["url"]), json.dumps(e["emoji"], ensure_ascii=False))
        if "explorer_name" in e:
            head += ' "explorer_name": %s,' % json.dumps(e["explorer_name"], ensure_ascii=False)
        L.append(head)
        b = e["bbox"]
        L.append('      "bbox": { "minLng": %s, "minLat": %s, "maxLng": %s, "maxLat": %s } }%s' % (
            json.dumps(b["minLng"]), json.dumps(b["minLat"]),
            json.dumps(b["maxLng"]), json.dumps(b["maxLat"]), tail))
    L.append("  ]")
    return "\n".join(L)


def sync_fleet(ws_path, src):
    """Rewrite ONLY the worksheet's "metro_explorers" value from the fleet
    manifest (metros.json), projecting away fleet-only fields like `repo`.
    Returns True if the worksheet changed."""
    if src.startswith("http://") or src.startswith("https://"):
        import urllib.request
        req = urllib.request.Request(src, headers={"User-Agent": "districtry-fleet-sync"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            manifest = json.loads(resp.read().decode("utf-8"))
    else:
        with open(src, encoding="utf-8") as f:
            manifest = json.load(f)
    entries = []
    for m in manifest["metros"]:
        e = {"id": m["id"], "label": m["label"], "url": m["url"], "emoji": m["emoji"], "bbox": m["bbox"]}
        if "explorer_name" in m:
            e["explorer_name"] = m["explorer_name"]
        entries.append(e)
    text = open(ws_path, encoding="utf-8", newline="").read()
    key = '"metro_explorers": ['
    i = text.index(key)
    depth = 0
    j = i + len(key) - 1
    for j in range(i + len(key) - 1, len(text)):
        if text[j] == "[":
            depth += 1
        elif text[j] == "]":
            depth -= 1
            if depth == 0:
                break
    else:
        fail("could not find the end of metro_explorers in %s" % ws_path)
    new_text = text[:i] + '"metro_explorers": ' + render_explorers_json(entries) + text[j + 1:]
    if new_text != text:
        open(ws_path, "w", encoding="utf-8", newline="").write(new_text)
        print("generate-metro-files: %s — metro_explorers synced from %s" % (ws_path, src))
        return True
    print("generate-metro-files: %s — metro_explorers already match %s" % (ws_path, src))
    return False


def split_regions(text, path):
    """Return (lines, {name: (begin_idx, end_idx)}) — marker line indices."""
    lines = text.split("\n")
    regions = {}
    open_name = None
    open_at = None
    for i, line in enumerate(lines):
        m = GENERATED_RE.match(line)
        if not m:
            continue
        kind, name = m.groups()
        if kind == "BEGIN":
            if open_name is not None:
                fail("%s:%d: GENERATED:BEGIN %s while %s is still open" % (path, i + 1, name, open_name))
            if name in regions:
                fail("%s:%d: duplicate GENERATED region %r" % (path, i + 1, name))
            open_name, open_at = name, i
        else:
            if name != open_name:
                fail("%s:%d: GENERATED:END %s does not match open region %r" % (path, i + 1, name, open_name))
            regions[name] = (open_at, i)
            open_name = None
    if open_name is not None:
        fail("%s: GENERATED region %s is never closed" % (path, open_name))
    return lines, regions


# The two head strings Google renders in a search result. Everything else in
# brand.head is a social-card string with its own, much looser, platform limit.
#
# These are budgets in CHARACTERS and Google truncates by PIXEL WIDTH (~600px
# of title, ~920px of snippet on desktop), so they are a proxy rather than the
# real rule — deliberately set a little under where truncation actually starts,
# because a wide string (capitals, em dashes) reaches the pixel limit sooner
# than a narrow one. Fitting is what matters: an overrun does not merely look
# untidy, it cuts the tail, and every one of the four descriptions that
# overran on 2026-09-08 cut the same words — "and who represents you. Free, no
# login." — which is the whole differentiator, dropped from the snippet on
# every result the app has ever shown.
SERP_LIMITS = {"title": 60, "description": 155}


def check_serp_lengths(ws_path, worksheet):
    """Hold brand.head.title and .description to what a search result shows.

    These strings are GENERATED into every instance's <title> and meta
    description, which is exactly why nothing had ever measured them: the
    generated-region gate proves the HTML matches the worksheet and asks
    nothing at all about what the worksheet says. Four of six titles and four
    of six descriptions were over the limit when this check was written.
    """
    head = worksheet.get("brand", {}).get("head")
    if not head:
        return
    for key, limit in sorted(SERP_LIMITS.items()):
        value = head.get(key)
        if value is None:
            continue
        if len(value) > limit:
            fail("%s: brand.head.%s is %d characters and Google shows about "
                 "%d — the last %d would be cut from the search result. "
                 "Shorten it; do not raise the limit. The tail is where the "
                 "differentiator lives.\n    %r"
                 % (ws_path, key, len(value), limit, len(value) - limit, value))

    # The result Google shows is often the only place a reader meets the app's
    # name, so the title must carry it whole. SF's smoke test has asserted this
    # in a browser since the rebrand and the other five instances asserted
    # nothing — this is that check, moved to where it covers every instance and
    # costs no browser.
    title = head.get("title")
    app_name = worksheet.get("brand", {}).get("app_name")
    if title and app_name and app_name not in title:
        fail("%s: brand.head.title does not carry brand.app_name %r, so a "
             "search result never names the app in full.\n    %r"
             % (ws_path, app_name, title))


def load_worksheet(ws_path, schema):
    """Read, schema-validate and sanity-check one instance's worksheet."""
    try:
        with open(ws_path, encoding="utf-8") as f:
            worksheet = json.load(f)
    except (OSError, ValueError) as e:
        fail("cannot read worksheet %s: %s" % (ws_path, e))
    try:
        jsonschema.validate(worksheet, schema)
    except jsonschema.ValidationError as e:
        fail("%s does not validate against the schema: %s (at %s)"
             % (ws_path, e.message, "/".join(str(p) for p in e.absolute_path) or "<root>"))

    check_serp_lengths(ws_path, worksheet)

    ranks = sorted(l["area_rank"] for l in worksheet["layers"])
    if ranks != list(range(1, len(ranks) + 1)):
        fail("%s: layers[].area_rank must be exactly 1..%d with no gaps or duplicates"
             % (ws_path, len(ranks)))
    anchor_ids = {a["layer"] for a in worksheet["anchors"]}
    layer_ids = {l["id"] for l in worksheet["layers"]}
    if not anchor_ids <= layer_ids:
        fail("%s: anchors reference unknown layer id(s): %s"
             % (ws_path, ", ".join(sorted(anchor_ids - layer_ids))))
    if "sources_page" in worksheet:
        if "verified_date" not in worksheet:
            fail("%s: sources_page is set but verified_date is not — the page prints "
                 "that date, and hand-writing it there is the drift this key exists to stop"
                 % ws_path)
        missing = [l["id"] for l in worksheet["layers"] if "source" not in l]
        if missing:
            fail("%s: sources_page is set, so every layer needs a source block; %d "
                 "lack one: %s" % (ws_path, len(missing), ", ".join(missing)))
    return worksheet


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".", help="repo root (default: .)")
    ap.add_argument("--instance", action="append", metavar="ID",
                    help="limit to one instance (repeatable; default: every instance)")
    ap.add_argument("--schema", default="schema/metro-worksheet.schema.json")
    ap.add_argument("--check", action="store_true",
                    help="verify committed regions match the worksheets; exit 1 on drift")
    ap.add_argument("--sync-fleet", nargs="?", const="", metavar="SRC",
                    help="refresh metro_explorers from the fleet manifest before generating "
                         "(SRC path/URL; default: repo-root metros.json, else %s)" % FLEET_URL)
    args = ap.parse_args()

    ids = args.instance or sorted(INSTANCES)
    unknown = [i for i in ids if i not in INSTANCES]
    if unknown:
        fail("unknown instance(s): %s (known: %s)"
             % (", ".join(unknown), ", ".join(sorted(INSTANCES))))

    schema_path = os.path.join(args.root, args.schema)
    try:
        with open(schema_path, encoding="utf-8") as f:
            schema = json.load(f)
    except (OSError, ValueError) as e:
        fail("cannot read schema %s: %s" % (schema_path, e))

    if args.sync_fleet is not None:
        if args.check:
            fail("--sync-fleet and --check are mutually exclusive (the CI gate stays hermetic)")
        src = args.sync_fleet
        if not src:
            local = os.path.join(args.root, "metros.json")
            src = local if os.path.exists(local) else FLEET_URL
        # Every instance carries the same fleet list, so every instance's
        # worksheet is synced — a launch that updated only one would put the
        # metro portal in one app out of step with the others.
        for instance in ids:
            try:
                sync_fleet(os.path.join(args.root, INSTANCES[instance]["worksheet"]), src)
            except (OSError, ValueError, KeyError) as e:
                fail("fleet sync of %s from %s failed: %s" % (instance, src, e))

    drift, processed = [], 0
    for instance in ids:
        inst = INSTANCES[instance]
        worksheet = load_worksheet(os.path.join(args.root, inst["worksheet"]), schema)
        # The apple-touch-icon href is the one generated brand value naming a
        # file on disk rather than carrying its own bytes (the favicon is a
        # data: URI). A tag pointing at a missing PNG is invisible in every
        # other gate and shows up only as a blank tile on someone's phone, so
        # the path is resolved here, where the instance directory is known.
        atouch = worksheet.get("brand", {}).get("apple_touch_icon")
        if atouch and not os.path.exists(os.path.join(args.root, inst["app"], atouch)):
            fail("%s: brand.apple_touch_icon names %s, which does not exist in %s/"
                 % (inst["worksheet"], atouch, inst["app"]))
        for rel_path, name, render in targets_for(worksheet, inst):
            path = os.path.join(args.root, rel_path)
            try:
                with open(path, encoding="utf-8", newline="") as f:
                    text = f.read()
            except OSError as e:
                fail("cannot read target %s (instance %s): %s" % (path, instance, e))
            lines, regions = split_regions(text, rel_path)
            if name not in regions:
                fail("%s has no GENERATED region %r — fences missing?" % (rel_path, name))
            begin, end = regions[name]
            current = "\n".join(lines[begin + 1:end])
            rendered = render(worksheet)
            processed += 1
            if args.check:
                if current != rendered:
                    drift.append((rel_path, name, current, rendered))
            elif current != rendered:
                new_lines = lines[:begin + 1] + rendered.split("\n") + lines[end:]
                with open(path, "w", encoding="utf-8", newline="") as f:
                    f.write("\n".join(new_lines))
                print("generate-metro-files: %s — region %r regenerated" % (rel_path, name))
            else:
                print("generate-metro-files: %s — region %r already current" % (rel_path, name))

    if args.check:
        if drift:
            for rel_path, name, current, rendered in drift:
                print("generate-metro-files: DRIFT in %s region %r:" % (rel_path, name), file=sys.stderr)
                for dl in difflib.unified_diff(current.splitlines(), rendered.splitlines(),
                                               fromfile="committed", tofile="regenerated", lineterm="", n=1):
                    print("  " + dl, file=sys.stderr)
            print("generate-metro-files: FAIL — %d region(s) drifted from their worksheet. "
                  "Edit the instance's metro-worksheet.json and regenerate; never hand-edit "
                  "a GENERATED region." % len(drift), file=sys.stderr)
            sys.exit(1)
        print("generate-metro-files: OK — all %d GENERATED regions across %d instance(s) "
              "match their worksheets" % (processed, len(ids)))
    else:
        print("generate-metro-files: OK — %d regions processed across %d instance(s)"
              % (processed, len(ids)))


if __name__ == "__main__":
    main()
