#!/usr/bin/env python3
"""
docs/ENDPOINT_INVENTORY.md — every external endpoint the apps call at runtime,
every dataset the build depends on, and the terms on each.

WHY THIS IS GENERATED. A hand-written inventory of this would be wrong within a
fortnight: the runtime host list moves whenever a county ships a layer that loads
live from its own GIS, the dataset counts move weekly, and the point-transmission
figures move whenever a loader is rerouted. Every figure below already has an
owner in the tree, so this reads them rather than restating them.

WHAT IT READS, AND FROM WHOM.

  * Runtime hosts — extracted from each instance's own index.html and sw.js and
    classified by PATH SHAPE (an ArcGIS /FeatureServer, a Socrata /resource,
    a known geocoder or tile host). That is the only way to tell a request this
    site MAKES from a link a reader CLICKS, and the split is most of this
    document's value: of the hosts those files name, fewer than a fifth are
    fetched.
  * Recipients, geocoders and their policy links — IMPORTED from
    build_privacy_page.py. That generator already owns the question "who receives
    what", and two readers of one question is where this fleet's recurring defect
    starts.
  * Point transmission — read from point-transmission.json, the artifact
    scripts/probe_point_transmission.mjs writes by booting each app in Chromium
    and counting the hooks that FIRE. Not from any prose: CLAUDE.md's paragraph
    said `ny 4` while the artifact said 5, which is exactly why this reads the
    artifact.
  * Layer totals — each instance's own metro-worksheet.json.
  * Dataset counts — each instance's validate_sources.py manifest and its own
    data/app directory.
  * Terms — LICENSE-DATA.md's own section headings. The terms are NOT restated
    here; this links to them. Restating a licence is how two copies come to
    disagree about what a publisher granted.

THE TWO READERS ARE HELD TO EACH OTHER. build_privacy_page.py measures, per app,
whether it reaches CARTO (`tiles`), cdnjs (`cdn`) and which geocoders. This
generator classifies hosts independently. check_against_privacy_page() requires
the two to agree app by app, so a classifier that stops recognising a tile host,
or a privacy-page regex that stops matching one, fails here rather than leaving
one of the two quietly wrong. That is the case neither can see alone.

THE "NOT RECORDED" CLAIMS ARE RE-AUDITED, and that is the subtle half. This
document says the repo records no licence for certain runtime services. Such a
claim rots in the DANGEROUS direction: someone records the term, and the document
goes on saying it is absent. So every entry in UNRECORDED_TERMS is checked
against the tree on every run, and the gate FAILS when the repo has started
recording one. Adding a term retires its entry; it does not sit there lying.

Usage:
    python3 scripts/build_endpoint_inventory.py            # write the document
    python3 scripts/build_endpoint_inventory.py --check     # the CI drift gate
"""

import collections
import difflib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_privacy_page as privacy                       # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO_ROOT, "docs", "ENDPOINT_INVENTORY.md")
LICENCE = "LICENSE-DATA.md"
TRANSMISSION = os.path.join(REPO_ROOT, "point-transmission.json")

URL_RE = re.compile(r'https?://([A-Za-z0-9._\-]+\.[A-Za-z]{2,})(/[^\s"\'`)>,\\]*)?')

# RESERVED NAMES ARE NOT ENDPOINTS. RFC 2606 and RFC 6761 set aside .invalid,
# .example, .test and .localhost precisely so they cannot resolve, and this fleet
# uses one on purpose: an instance with no Socrata portal sets
# `SOCRATA_HOST = "https://data.invalid"`, so the shared engine block is present
# and its loader can never reach anything. Counting that as a runtime endpoint
# would claim a request nobody makes; counting it as a link would claim one a
# reader could follow. It is neither, so it is excluded and the count is PRINTED
# rather than dropped silently.
RESERVED_RE = re.compile(r"\.(invalid|example|test|localhost)$|^example\.(com|org|net|gov)$")

# A host is classified ONCE, by the strongest kind any of its URLs matches. A
# first draft summed per-kind totals and let one host land in two buckets when it
# appeared with both a service path and a link path, which inflated the total.
KIND_ORDER = ["geocoder", "basemap tiles", "library CDN", "analytics",
              "webfont host", "Census TIGERweb", "Socrata", "ArcGIS",
              "link or citation"]
RUNTIME_KINDS = [k for k in KIND_ORDER if k != "link or citation"]

# Socrata portals whose dataset URLs are built at runtime, so no /resource/ path
# appears as a literal. Measured from the tree by --check (see
# check_socrata_hosts), which fails on a portal this list does not name.
SOCRATA_HOSTS = re.compile(
    r"^data\.(cityofchicago|sfgov|cityofnewyork|milwaukee|macoupincountyil|nysed)\.")

# Terms this repository does NOT record, re-audited every run. `probe` is a
# regex; if the tree starts matching it, the entry is stale and the gate fails.
UNRECORDED_TERMS = [
    ("Leaflet and MapLibre GL licence terms",
     r"(BSD-2|BSD-3)[- ]Clause",
     "Both are permissive open-source projects and neither licence is stated "
     "anywhere in this repository. Not asserted here from memory."),
    ("Photon / Komoot service terms",
     r"komoot[^\n]{0,80}(terms|usage polic|rate limit)",
     "Only a privacy-policy link is on file. Photon's rate and attribution "
     "terms are not recorded."),
    ("NYC GeoSearch service terms",
     r"planninglabs[^\n]{0,80}(terms|usage polic|licen)",
     "Only a privacy-policy link is on file."),
    ("Nominatim Usage Policy",
     r"(operations\.osmfoundation\.org|Nominatim Usage Policy)",
     "Not cited, though the Illinois POI geocoder's worksheet posture "
     "(a serial queue at one second or more) is consistent with it."),
]


def fail(msg):
    print("build-endpoint-inventory: FAIL — " + msg, file=sys.stderr)
    sys.exit(1)


def read(rel):
    path = rel if os.path.isabs(rel) else os.path.join(REPO_ROOT, rel)
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError as e:
        fail("cannot read %s: %s" % (rel, e))


def instance_tags():
    """The fleet, from metros.json, via the generator that already reads it."""
    return [a["tag"] for a in privacy.load_apps() if a.get("tag")]


def classify(host, path):
    p = path.lower()
    if host in privacy.GEOCODERS:
        return "geocoder"
    if "cartocdn.com" in host:
        return "basemap tiles"
    if host == "cdnjs.cloudflare.com":
        return "library CDN"
    if "goatcounter" in host or "googletagmanager" in host or "google-analytics" in host:
        return "analytics"
    if "fonts.googleapis" in host or "fonts.gstatic" in host:
        return "webfont host"
    if "tigerweb" in host or host.endswith(".census.gov"):
        return "Census TIGERweb"
    if (re.search(r"/resource/[\w-]+\.(json|geojson|csv)", p) or "/api/views" in p
            or SOCRATA_HOSTS.search(host)):
        return "Socrata"
    if (re.search(r"/(featureserver|mapserver)", p) or "/arcgis/rest" in p
            or "/rest/services" in p):
        return "ArcGIS"
    return "link or citation"


_SCAN_CACHE = {}


def scan_hosts(tags):
    """{host: (kind, {tags})} over every instance's index.html and sw.js.

    Cached per tag set, because --check asks for the scan twice (once to render
    and once to count) and the reserved-name notice printed twice reads like two
    findings rather than one.
    """
    key = tuple(tags)
    if key in _SCAN_CACHE:
        return _SCAN_CACHE[key]
    kind_of, seen_in, reserved = {}, collections.defaultdict(set), set()
    for tag in tags:
        for rel in ["%s/index.html" % tag, "%s/sw.js" % tag]:
            if not os.path.exists(os.path.join(REPO_ROOT, rel)):
                continue
            src = read(rel)
            for m in URL_RE.finditer(src):
                host, path = m.group(1).lower(), m.group(2) or ""
                if RESERVED_RE.search(host):
                    reserved.add(host)
                    continue
                kind = classify(host, path)
                seen_in[host].add(tag)
                if host not in kind_of or KIND_ORDER.index(kind) < KIND_ORDER.index(kind_of[host]):
                    kind_of[host] = kind
    if reserved:
        print("build-endpoint-inventory: %d reserved name(s) excluded as "
              "unresolvable by design: %s"
              % (len(reserved), ", ".join(sorted(reserved))))
    _SCAN_CACHE[key] = {h: (kind_of[h], seen_in[h]) for h in kind_of}
    return _SCAN_CACHE[key]


def check_against_privacy_page(hosts, tags):
    """The two readers must agree, app by app, about tiles, cdnjs and geocoders."""
    apps = {a["tag"]: a for a in privacy.load_apps() if a.get("tag")}
    for tag in tags:
        app = apps.get(tag)
        if app is None:
            fail("%s is in the fleet but build_privacy_page measured no app for "
                 "it — the two readers disagree about what the fleet is" % tag)
        mine = {kind: {h for h, (k, ts) in hosts.items() if k == kind and tag in ts}
                for kind in RUNTIME_KINDS}
        for kind, flag in (("basemap tiles", "tiles"), ("library CDN", "cdn")):
            theirs = bool(app.get(flag))
            if bool(mine[kind]) != theirs:
                fail("%s: this generator finds %d %s host(s) while "
                     "build_privacy_page measures %s=%r. One of the two readers "
                     "is wrong about a request a reader's browser makes."
                     % (tag, len(mine[kind]), kind, flag, theirs))
        if set(app.get("geocoders") or []) != mine["geocoder"]:
            fail("%s: geocoder hosts disagree — build_privacy_page has %s, this "
                 "generator finds %s" % (tag, sorted(app.get("geocoders") or []),
                                         sorted(mine["geocoder"])))


def check_socrata_hosts(hosts):
    """A Socrata portal reached only by a built URL must be in SOCRATA_HOSTS."""
    for host, (kind, _tags) in hosts.items():
        if kind != "Socrata" and re.match(r"^data\.[a-z0-9.\-]+$", host):
            fail("%s looks like an open-data portal and is classified %r. If it "
                 "serves Socrata datasets, add it to SOCRATA_HOSTS; if it does "
                 "not, this check needs narrowing." % (host, kind))


def check_no_webfont_host(hosts):
    """A webfont host would be a recipient nothing on the privacy page names."""
    fonts = sorted(h for h, (k, _t) in hosts.items() if k == "webfont host")
    if fonts:
        fail("an external webfont host is reached: %s. The fonts are meant to be "
             "self-hosted per instance; a font CDN is a recipient the privacy "
             "page does not name." % ", ".join(fonts))


def check_unrecorded_terms():
    """Fail when the repo has started recording a term this document calls absent.

    THIS FILE AND THE DOCUMENT IT WRITES ARE BOTH EXCLUDED FROM THE SURFACE, and
    the first draft was not: UNRECORDED_TERMS lives here, so the entry
    "Photon / Komoot service terms" matched its own probe and the gate failed
    claiming somebody had recorded the term. A probe that can read its own
    declaration measures nothing.
    """
    mine = os.path.basename(os.path.abspath(__file__))
    surface = []
    for base, _dirs, files in os.walk(REPO_ROOT):
        if any(part in base for part in (".git", "node_modules", "__pycache__")):
            continue
        for fn in files:
            if fn.endswith((".py", ".md", ".json")) and fn not in (os.path.basename(OUT), mine):
                surface.append(os.path.join(base, fn))
    blob = "\n".join(read(p) for p in surface)
    for label, probe, _why in UNRECORDED_TERMS:
        if re.search(probe, blob, re.I):
            fail("UNRECORDED_TERMS still says %r is not recorded, but the tree "
                 "now matches %r. Someone recorded the term — retire the entry "
                 "rather than leaving this document claiming it is missing."
                 % (label, probe))
    print("build-endpoint-inventory: %d unrecorded-term entr(y/ies) re-audited, "
          "none has started being recorded" % len(UNRECORDED_TERMS))


def library_pins():
    """(name, version) for each cdnjs asset, from the app that loads them."""
    pins = set()
    for tag in instance_tags():
        rel = "%s/index.html" % tag
        if not os.path.exists(os.path.join(REPO_ROOT, rel)):
            continue
        for m in re.finditer(r"cdnjs\.cloudflare\.com/ajax/libs/([\w\-.]+)/([\w.]+)/",
                             read(rel)):
            pins.add((m.group(1), m.group(2)))
    if not pins:
        fail("no cdnjs asset found in any app — either the CDN pin moved or this "
             "pattern no longer matches it")
    return sorted(pins)


def transmission(totals):
    """{tag: count of layers that send the selected point}, from the artifact.

    THE ARTIFACT CARRIES BOTH A COUNT AND THE LIST IT COUNTS, so the two are
    required to agree — an artifact that disagrees with itself is not a
    measurement. And its `layer_ids` are required to match the worksheet's own
    layer count, which makes a STALE PROBE fail here: add a layer and the browser
    probe has to run again before this document can claim anything about it. That
    is the same posture build_privacy_page.py takes with its fingerprint.
    """
    try:
        data = json.loads(read(TRANSMISSION))
    except ValueError as e:
        fail("point-transmission.json is not valid JSON: %s" % e)
    apps = data.get("apps")
    if not isinstance(apps, dict):
        fail("point-transmission.json has no `apps` object — the artifact's shape "
             "moved and this generator reads it by that key")
    out = {}
    for tag in totals:
        rec = apps.get(tag)
        if not isinstance(rec, dict):
            fail("point-transmission.json has no entry for %s, which is in the "
                 "fleet — re-run scripts/probe_point_transmission.mjs" % tag)
        count, listed = rec.get("layers_sending_point"), rec.get("layers")
        if not isinstance(count, int) or not isinstance(listed, list):
            fail("point-transmission.json's %s entry has no "
                 "`layers_sending_point` int and `layers` list" % tag)
        if count != len(listed):
            fail("point-transmission.json's %s entry counts %d layers sending the "
                 "point and lists %d — the artifact disagrees with itself"
                 % (tag, count, len(listed)))
        ids = rec.get("layer_ids")
        if not isinstance(ids, list) or len(ids) != totals[tag]:
            fail("point-transmission.json saw %s layer(s) in %s while its "
                 "worksheet declares %d — the probe is STALE. Re-run "
                 "scripts/probe_point_transmission.mjs before this document can "
                 "describe that instance."
                 % (len(ids) if isinstance(ids, list) else "no", tag, totals[tag]))
        out[tag] = count
    return out


def layer_totals():
    """{tag: len(worksheet layers)} — the same list that drives EXPECT_LAYER_IDS."""
    out = {}
    for tag in instance_tags():
        rel = "metro-worksheet.json" if tag == "il" else "%s/metro-worksheet.json" % tag
        try:
            w = json.loads(read(rel))
        except ValueError as e:
            fail("%s is not valid JSON: %s" % (rel, e))
        out[tag] = len(w.get("layers") or [])
        if not out[tag]:
            fail("%s declares no layers[] — this document counts them from the "
                 "worksheet that owns them" % rel)
    return out


def dataset_counts():
    """{tag: (manifest entries, data/app json files, blocked sources)}."""
    out = {}
    for tag in instance_tags():
        rel = ("scripts/validate_sources.py" if tag == "il"
               else "%s/scripts/validate_sources.py" % tag)
        if not os.path.exists(os.path.join(REPO_ROOT, rel)):
            fail("%s has no validate_sources.py — that manifest is the authority "
                 "on which datasets the build depends on" % tag)
        src = read(rel)
        appdir = os.path.join(REPO_ROOT, tag, "data", "app")
        files = len([f for f in os.listdir(appdir) if f.endswith(".json")]) \
            if os.path.isdir(appdir) else 0
        # BOTH CLASSES COUNT AS A SOURCE REFUSING US, and they are different
        # mechanisms rather than different prose: `blocked` is measured
        # unreachable and is re-probed, because probing is how you learn an
        # outage ended; `robots_declined` is a host that asked us not to read it
        # and is NEVER fetched, because the fetch is the thing being asked for —
        # only its robots.txt is re-read. Counting one and not the other would
        # understate what refuses this project.
        out[tag] = (src.count('"layer":'), files,
                    src.count('"blocked":') + src.count('"robots_declined":'))
    return out


def manifest_hosts():
    hosts = set()
    for tag in instance_tags():
        rel = ("scripts/validate_sources.py" if tag == "il"
               else "%s/scripts/validate_sources.py" % tag)
        hosts |= {m.group(1).lower() for m in URL_RE.finditer(read(rel))}
    return hosts


def licence_sections():
    """The numbered categories in LICENSE-DATA.md, by their own headings."""
    text = read(LICENCE)
    cats = re.findall(r"^### (\d+\. .+)$", text, re.M)
    if len(cats) < 4:
        fail("LICENSE-DATA.md has %d numbered term categories; this document "
             "summarises them and needs at least the four on record" % len(cats))
    for want in ("ODbL", "Attribution", "Warranty"):
        if not re.search(r"^#+ .*%s" % want, text, re.M | re.I):
            fail("LICENSE-DATA.md has no %r heading — this document points at it "
                 "by section rather than restating the terms" % want)
    return cats


def anchor(heading):
    a = heading.lower()
    a = re.sub(r"[^\w\s-]", "", a)
    return "#" + re.sub(r"\s+", "-", a.strip())


def render():
    tags = instance_tags()
    hosts = scan_hosts(tags)
    check_against_privacy_page(hosts, tags)
    check_socrata_hosts(hosts)
    check_no_webfont_host(hosts)
    by_kind = collections.defaultdict(dict)
    for host, (kind, ts) in hosts.items():
        by_kind[kind][host] = ts
    runtime_total = sum(len(by_kind.get(k, {})) for k in RUNTIME_KINDS)
    links = len(by_kind.get("link or citation", {}))
    pins = library_pins()
    totals = layer_totals()
    sends = transmission(totals)
    counts = dataset_counts()
    cats = licence_sections()

    L = []
    w = L.append
    w("<!-- GENERATED by scripts/build_endpoint_inventory.py — do NOT hand-edit.")
    w("     Every figure here is read from the file that owns it. Change the tree")
    w("     and regenerate; `--check` in CI fails on drift. -->")
    w("")
    w("# Endpoint and dataset inventory")
    w("")
    w("What the apps contact while a reader uses them, what the build depends on,")
    w("and the terms on each. **Generated** — see the generator's docstring for")
    w("which file each figure is read from, and why none of them is restated here.")
    w("")
    w("## 1. Runtime endpoints — what the browser contacts")
    w("")
    w("Hosts are extracted from each instance's own `index.html` and `sw.js` and")
    w("classified by **path shape**, which is what separates a request this site")
    w("makes from a link a reader clicks. Of **%d distinct hosts** those files"
      % (runtime_total + links))
    w("name, **%d are fetched by the browser**; the other %d are links."
      % (runtime_total, links))
    w("")
    for kind in RUNTIME_KINDS:
        hs = by_kind.get(kind, {})
        if not hs and kind != "webfont host":
            continue
        if kind == "webfont host":
            w("### Webfonts — none")
            w("")
            w("**No external font host.** Barlow is self-hosted per instance, and")
            w("`check_no_webfont_host()` fails the build if that stops being true —")
            w("a font CDN would be a recipient the privacy page does not name.")
            w("")
            continue
        w("### %s — %d host(s)" % (kind[0].upper() + kind[1:], len(hs)))
        w("")
        w("| host | instances |")
        w("|---|---|")
        for host in sorted(hs):
            w("| `%s` | %s |" % (host, ", ".join(t for t in tags if t in hs[host])))
        w("")
        if kind == "geocoder":
            w("The most sensitive flow on the site: it is **the text a reader")
            w("types**. `build_privacy_page.py` owns what each receives and links")
            w("each one's policy; this table is held to that generator's own")
            w("per-app measurement, so the two cannot disagree.")
            w("")
        if kind == "library CDN":
            w("Pinned: " + ", ".join("**%s %s**" % (n, v) for n, v in pins) + ".")
            w("")
        if kind == "basemap tiles":
            w("One service. Several host spellings appear because the tile URL is a")
            w("`{s}.` template and some are `preconnect` hints — one recipient, not")
            w("several.")
            w("")
    w("### Which services receive a reader's selected point")
    w("")
    w("Measured in a real browser by `scripts/probe_point_transmission.mjs`, which")
    w("replaces every `.atPoint` hook with a recorder and counts the ones that")
    w("**fire**. No static read can answer this and two earlier attempts")
    w("overcounted, so this is read from `point-transmission.json` and never from")
    w("prose.")
    w("")
    w("| instance | layers that send the point | registered layers |")
    w("|---|---|---|")
    for tag in tags:
        w("| %s | %s | %d |" % (tag, sends.get(tag, "not measured"), totals[tag]))
    w("")
    w("## 2. Build-time datasets")
    w("")
    w("| instance | manifest entries | shipped `data/app` files | sources measured as blocking |")
    w("|---|---|---|---|")
    tm = ta = tb = 0
    for tag in tags:
        m, a, b = counts[tag]
        tm, ta, tb = tm + m, ta + a, tb + b
        w("| %s | %d | %d | %d |" % (tag, m, a, b))
    w("| **total** | **%d** | **%d** | **%d** |" % (tm, ta, tb))
    w("")
    w("**%d distinct source hosts** across the six manifests. Each instance's"
      % len(manifest_hosts()))
    w("`validate_sources.py` is the authority — it carries every dataset id and")
    w("provenance URL the build depends on, and is machine-checked monthly. Two")
    w("entry classes mean the source refuses this client, and the check")
    w("**inverts** for both: the refusal is expected and its LIFTING is the signal")
    w("a human can act on. They differ in whether anything is fetched. A")
    w("`blocked` entry was measured unreachable and IS re-probed, because probing")
    w("is how you learn an outage ended. A `robots_declined` entry is a host whose")
    w("own robots.txt asks this client not to read it, and is NEVER fetched — the")
    w("request is the thing being asked for, so only robots.txt is re-read.")
    w("")
    w("## 3. Terms")
    w("")
    w("[`LICENSE-DATA.md`](../%s) is the authority and the terms are **not**"
      % LICENCE)
    w("restated here — restating a licence is how two copies come to disagree")
    w("about what a publisher granted. Code is Apache 2.0; the compiled databases")
    w("are ODbL v1.0, a grant over *the compilation* and explicitly not over the")
    w("underlying records. The categories of underlying terms it records:")
    w("")
    for c in cats:
        w("- [%s](../%s%s)" % (c, LICENCE, anchor(c)))
    w("")
    w("See also its [Attribution](../%s#attribution) and [Warranty](../%s#warranty)"
      % (LICENCE, LICENCE))
    w("sections. Two runtime things that document deliberately does not cover are")
    w("the map tiles and the geocoding, both of which run on OpenStreetMap data;")
    w("it also records that **no shipped boundary is derived from OpenStreetMap**.")
    w("")
    w("### Where a term is recorded, and where it is not")
    w("")
    w("Per-source terms live next to the data they govern — in the builder that")
    w("produced the file and on that instance's `sources.html`. What is **not**")
    w("recorded anywhere in this repository, and is therefore a gap in this")
    w("inventory rather than a fact it can assert:")
    w("")
    for label, _probe, why in UNRECORDED_TERMS:
        w("- **%s.** %s" % (label, why))
    w("")
    w("Each of those is re-audited on every run: if the repository starts")
    w("recording one, this build **fails** rather than going on calling it absent.")
    w("Most of the government feature services above carry no recorded licence")
    w("either. What *is* recorded per host is the **access posture** — the")
    w("robots.txt reading, the client measurements, the `blocked` flags — which is")
    w("a different question from a licence grant.")
    return "\n".join(L) + "\n"


def main():
    check = "--check" in sys.argv[1:]
    rendered = render()
    check_unrecorded_terms()
    if check:
        if not os.path.exists(OUT):
            fail("docs/ENDPOINT_INVENTORY.md is missing — generate it with "
                 "`python3 scripts/build_endpoint_inventory.py`")
        current = read(OUT)
        if current != rendered:
            for dl in list(difflib.unified_diff(
                    current.splitlines(), rendered.splitlines(),
                    fromfile="committed docs/ENDPOINT_INVENTORY.md",
                    tofile="regenerated", lineterm="", n=1))[:40]:
                print("  " + dl, file=sys.stderr)
            fail("docs/ENDPOINT_INVENTORY.md has drifted from the tree it "
                 "describes — regenerate it rather than editing it by hand.")
        print("build-endpoint-inventory: OK — current; %d runtime host(s) across "
              "%d instance(s)" % (
                  sum(1 for h, (k, _t) in scan_hosts(instance_tags()).items()
                      if k != "link or citation"), len(instance_tags())))
        return
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        f.write(rendered)
    print("build-endpoint-inventory: wrote docs/ENDPOINT_INVENTORY.md (%d bytes)"
          % len(rendered))


if __name__ == "__main__":
    main()
