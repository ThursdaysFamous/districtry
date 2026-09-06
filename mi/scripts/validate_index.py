#!/usr/bin/env python3
"""
Post-rewrite sanity gate for the app and its generated data files.

The weekly roster workflows regenerate the officeholder rosters under
data/app/*.json (scripts/build_il_roster.py, build_cpd_roster.py) and open a
PR. Those builders validate their *input* (they refuse an incomplete roster),
but this script is the *output*-side gate: run it after any regeneration and
before opening a PR to confirm the app and its data are still coherent.

Before the P0 externalization these datasets were spliced into object literals
inside index.html and the risk was a mis-anchored regex dropping live code.
Now the builders emit plain JSON with json.dump (no splice, no escaping), so the
checks here are: index.html still parses and carries every layer, it no longer
embeds any dataset inline, and every app-data file is present and well formed.

Checks (all must pass; exits non-zero on the first failure):
  1. The main inline <script> still parses (`node --check`).
  2. registerLayer( appears at least as many times as expected, AND every layer
     id in EXPECT_LAYER_IDS is registered. Most layers register through the
     factories, so a lost factory-registered module would not move the raw
     registerLayer( count — the per-id check catches that (ported from the NYC
     fork per docs/ENGINE_SYNC.md backlog item 8, "port checks, not bytes").
  3. index.html embeds no dataset inline (no `JSON.parse('...')` blobs remain)
     and references each data/app/* file it fetches.
  4. Every expected data/app/*.json exists, parses, and has the right shape.
  5. LAYER_AREA_RANK lists every registered layer id exactly once and nothing
     else — the z-order honesty rule made executable so a layer can never be
     registered but forgotten in the stack (or vice versa).
  6. METRO_EXPLORERS entries are well formed (id/label/https url; bbox, when
     present, is a sane min<max box that does NOT contain this metro's own
     center — a bbox covering home would make the sibling-metro portal easter
     egg fire on every pan). Guards the copy-verbatim config diff every fork
     applies when a new metro launches.
  7. sw.js exactly-one-list invariant: every data/app/*.json on disk is
     cached in exactly one of the service worker's GEOMETRY_URLS / ROSTER_URLS,
     so no data file is ever un-cached or double-listed.
  8. Every county with a per-county dispatch entry is inside the scope mask's
     county list, DERIVED from index.html rather than from a hand-kept list.
     The wash claims "beyond here only the statewide layers answer"; this is
     what stops that claim going stale, as it did for LaSalle, Kankakee, Boone
     and Grundy across two research passes with no gate noticing.

Usage:
    python3 scripts/validate_index.py [path/to/index.html]
"""

import json
import os
import re
import subprocess
import sys
import tempfile

# Machine-readable capability declaration (docs/MECHANIZATION_PLAYBOOK.md,
# Conversion 3). The fleet-status workflow in the CHI repo parses this list
# from every fork's validator and diffs it against CHI's: a capability present
# in a fork but absent here is a reverse-parity WARN — the mechanical form of
# "fork-born validator improvements must land in CHI within one release
# cycle". Shape contract (CHI is the master): a module-level list literal
# named CAPABILITIES of kebab-case strings, one per distinct check this
# validator actually performs. Add an entry when you add a check; never
# declare a capability the code doesn't have.
CAPABILITIES = [
    "engine-fence-lint",        # 0/0c: ENGINE markers well formed, index.html + sw.js
    "metro-explorers-lint",     # 0b: portal list shape/bbox sanity
    "inline-script-parses",     # 1: node --check on the main inline script
    "register-layer-floor",     # 2: raw registerLayer( count floor
    "expect-layer-ids",         # 2: every expected layer id registered
    "layer-area-rank-lint",     # 2b: rank array covers the id set exactly
    "layer-sidebar-rank-lint",  # 2c: sidebar rank covers the id set exactly
    "no-inline-datasets",       # 3: no JSON.parse blobs; data files referenced
    "data-file-shapes",         # 4: every data/app file exists with sane counts
    "sw-exactly-one-list",      # 5: each data file cached in exactly one sw list
    "negative-point-ground-truth",  # 4b: worksheet negative point misses every anchor geometry (born in NYC; back-ported per the ENGINE_SYNC DoD)
    "county-coverage-ring",     # 8: dispatched counties are all inside the scope mask
    "sources-page-coverage",    # 6: the public sources page covers every layer and the app links it
]

# The constants below are GENERATED from metro-worksheet.json (Conversion 2 —
# edit the worksheet, run scripts/generate_metro_files.py). Fork history worth
# keeping by hand: this instance's registerLayer floor arithmetic is 1 function
# definition + 5 factory bodies + 3 direct registerLayer() calls (county, and
# phase 3's county-subdivision and municipality) = 9 today, against a floor of
# 6. THE PARAGRAPH THAT USED TO SIT HERE WAS ILLINOIS'S, inherited verbatim
# when this validator was cloned: it described 11 direct calls, a
# police-station/fire-station move and a township layer, none of which this
# instance has ever had. The same stale paragraph is still in ia/ and wi/.
# ==== GENERATED:BEGIN validator-config ====
# Floor, not a moving target: new layers only raise this; a drop means
# modules were lost.
MIN_REGISTER_LAYER = 10

# Every layer id that must be registered in index.html. Most modules register
# through the factories, so deleting one would NOT lower the raw registerLayer(
# count above — this per-id list is the direct module-loss guard. Emitted in
# LAYER_AREA_RANK order; check 5 keeps the two naming the same set.
EXPECT_LAYER_IDS = [
    "us-house", "mi-senate", "county", "mi-house", "school-district-unified",
    "school-district-elementary", "county-commissioner", "county-subdivision",
    "zip-code", "city-ward", "precinct", "municipality", "police-station",
    "fire-station", "post-office",
]

# file -> (min features, max features) for the boundary layers fetched by the app.
GEOMETRY_FILES = {
    "metro-outline.json": (1, 1),  # The whole-Michigan-state outline for the coverage wash (loadMetroOutline), dissolved from all 83 counties' TIGERweb State_County layer-1 geometry by mi/scripts/build_metro_outline.py (METRO_COUNTY_FIPS = every county; DISPATCH_COUNTY_FIPS empty — no layer is county-keyed yet). Michigan is 2-band coverage: every layer answers statewide, so there is no wider region band. It dissolves to ONE ring, 1,716 vertices — TIGERweb's county fabric is WATER-INCLUSIVE (Keweenaw County alone spans 2.57 degrees of longitude, out past Isle Royale), so the two peninsulas and every Great Lakes island tile continuously through county water rather than sitting apart. A mid-lake point therefore reads inside coverage, which is correct — that water is assigned to Michigan counties — and is why the negative point is on land in Ohio rather than out on the water.
    "state-counties.json": (83, 83),  # Every county, pre-built from TIGERweb State_County layer 1.
    "congress-districts.json": (13, 13),  # U.S. House districts, pre-built from TIGERweb Legislative layer 0 (field CD120 — the 120th Congress; CD119 is retired and its query 400s).
    "mi-senate-districts.json": (38, 38),  # Michigan Senate districts, pre-built by mi/scripts/build_legislative_boundaries.py (2,000-point agreement gate).
    "mi-house-districts.json": (110, 110),  # Michigan House districts, pre-built by mi/scripts/build_legislative_boundaries.py (2,000-point agreement gate).
    "mi-commissioner-districts.json": (619, 619),  # All 619 county commissioner districts across all 83 counties, pre-built by mi/scripts/build_mi_commissioner_districts.py from the Bureau of Elections' statewide compilation (2,000-point agreement gate at 100.00%, per-county 1..N numbering check, MCL 46.401(1) 5..21 board-size check, and a guard that REFUSES the file if the source's Commissioner/Party columns ever reach data/app/). 611 of 619 carry an apportionment population; Baraga District 1 and all seven Cheboygan districts do not, and the card omits the row rather than showing a blank.
    "mi-precincts.json": (3895, 3895),  # 2026-cycle voting precincts, mi/scripts/build_mi_precincts.py. Exact band, not a floor: the builder refuses to write any count but 3,895, because on a cycle-scoped layer a count change is real information (Michigan went 4,340 -> 3,895 between the 2024 and 2026 maps) rather than drift.
    "mi-detroit-council-districts.json": (7, 7),  # Detroit's seven City Council districts, mi/scripts/build_mi_detroit_council.py. Exact band: the council's district seats are fixed at seven by the city charter, so any other count is a source change wanting a human, not drift.
    "mi-grand-rapids-wards.json": (3, 3),  # Grand Rapids's three City Commission wards, from the city's own ArcGIS org. Built by mi/scripts/build_mi_grand_rapids_wards.py, whose currency gate is the state's own 2026 precinct layer.
    "mi-warren-wards.json": (5, 5),  # Warren's five council wards, from the city's own ArcGIS account (item snippet "Approved 1/10/2023 Updated Labels 4-30-24"), built by mi/scripts/build_mi_warren_wards.py. THE WARD LAYER IS AT SERVICE INDEX 32, not 0 — a hardcoded /0 returns HTTP 200 with no features key and dies with a KeyError that reads like an outage; the builder reads the FeatureServer root and asserts the layer's name. The item states NO terms and is shared public (the Detroit case, not Lansing's CC BY-NC), and the builder REFUSES to rebuild if the city ever adds a licence, so geometry is never republished under terms nobody has read. Currency is measured, not assumed: dissolved by the state's own 2026 precinct WARD column (53 precincts, 10/10/11/11/11) the wards agree on 99.550% of 4,000 sampled points. The five wards tile the city EXACTLY — 139,387 against the Census place's 139,387 with zero blocks on the wrong side, Detroit's identity rather than Grand Rapids's bounded edge disagreement — and balance runs -2.46% to +3.78% on Census 2020.
}

# file -> minimum key count (officeholder rosters).
ROSTER_FILES = {
    "congress-roster.json": 13,  # U.S. House roster, refreshed weekly by update-mi-congress-roster.yml.
    "mi-senate-members.json": 34,  # Senate roster from Open States mi.csv enriched by the Michigan Senate's own all-senators directory, refreshed weekly by update-mi-legislature-roster.yml; floor tolerates transient vacancies (38 seats).
    "mi-house-members.json": 99,  # House roster from Open States mi.csv, refreshed weekly by update-mi-legislature-roster.yml; floor tolerates transient vacancies (110 seats). No capitol contact block — see the layer's source note.
    "coverage-gaps.json": 0,  # The Data gaps panel's content; empty at arrival — this instance's first recorded gap ships with the layer it belongs to.
    "mi-detroit-council-members.json": 4,  # Detroit's nine council members — seven by district plus two at large (charter Art. 4 §4-101). Built by mi/scripts/build_mi_detroit_council_roster.py from mi_detroit_council_scraper.py's cache. Five top-level keys: districts, citywide, office (the body's own address and switchboard, hoisted), sourceUrl, archivedAt.
    "mi-grand-rapids-council-members.json": 5,  # Grand Rapids's City Commission — six of seven seats, the city publishing no second Ward 1 commissioner. Built by mi/scripts/build_mi_grand_rapids_council.py from mi_grand_rapids_council_scraper.py's cache. Seven top-level keys: wards, citywide, office (the city switchboard and City Hall, hoisted), seats, seatsPerWard (how many commissioners a ward elects — the card counts the shortfall against it rather than hardcoding the city's arithmetic), vacancies (per ward: the cause, the predecessor, the date and the city page that states them — the card renders the explanation from this rather than from a literal, so one ward's resignation cannot appear on another ward's card), sourceUrl.
}

# Files the app references DYNAMICALLY — the URL is built from a slug at
# runtime (the gaps panel's <slug>-county-outline.json contract), so no
# literal appears in index.html. Exempt from the reference check only;
# existence, shape and the negative-point test still apply.
DYNAMIC_REFERENCE = frozenset({
})
# ==== GENERATED:END validator-config ====


def fail(msg):
    print("validate_index: FAIL — " + msg, file=sys.stderr)
    sys.exit(1)


# ENGINE fence lint (docs/ENGINE_SYNC.md): the cross-fork byte comparison is
# scripts/check_engine_parity.py's job; this merge gate only guards fence
# structure so a bad edit can't silently break the parity check itself.
ENGINE_MARKER_RE = re.compile(
    r"^[ \t]*(?:/\*|<!--)[ \t]*==== ENGINE:(BEGIN|END) ([a-z0-9][a-z0-9-]*) ====[ \t]*(?:\*/|-->)[ \t]*$"
)


def check_engine_markers(html):
    open_name = None
    names = set()
    for lineno, line in enumerate(html.splitlines(), 1):
        m = ENGINE_MARKER_RE.match(line)
        if not m:
            continue
        kind, name = m.groups()
        if kind == "BEGIN":
            if open_name is not None:
                fail("line %d: ENGINE:BEGIN %s while %s is still open" % (lineno, name, open_name))
            if name in names:
                fail("line %d: duplicate ENGINE block name %r" % (lineno, name))
            open_name = name
            names.add(name)
        else:
            if name != open_name:
                fail("line %d: ENGINE:END %s does not match open block %r" % (lineno, name, open_name))
            open_name = None
    if open_name is not None:
        fail("ENGINE block %s is never closed" % open_name)
    if not names:
        fail("no ENGINE blocks found — fences were deleted? (docs/ENGINE_SYNC.md)")
    return len(names)


def _split_object_literals(block):
    """Split the body of a JS array literal into its top-level {...} entries
    (depth-tracked, so nested objects like bbox stay inside their entry)."""
    entries, depth, start = [], 0, None
    for i, ch in enumerate(block):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                entries.append(block[start:i + 1])
                start = None
    return entries


def check_metro_explorers(html):
    """Lint the METRO_EXPLORERS config list (the copy-verbatim cross-fork
    diff applied whenever a new metro launches — the likeliest place for a
    future typo to land). bbox drives the sibling-metro portal easter egg."""
    m = re.search(r'var THIS_METRO = "([a-z0-9-]+)"', html)
    if not m:
        fail("could not find THIS_METRO in the METRO config block")
    this_metro = m.group(1)
    m = re.search(r"var METRO_CENTER = \[\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\]", html)
    if not m:
        fail("could not find METRO_CENTER in the METRO config block")
    center_lat, center_lng = float(m.group(1)), float(m.group(2))
    m = re.search(r"var METRO_EXPLORERS = \[(.*?)\n\s*\];", html, re.DOTALL)
    if not m:
        fail("could not find the METRO_EXPLORERS list in the METRO config block")
    entries = _split_object_literals(m.group(1))
    if not entries:
        fail("METRO_EXPLORERS is empty")

    ids = []
    for entry in entries:
        eid = re.search(r'\bid:\s*"([^"]*)"', entry)
        label = re.search(r'\blabel:\s*"([^"]*)"', entry)
        url = re.search(r'\burl:\s*"([^"]*)"', entry)
        if not (eid and eid.group(1)):
            fail("METRO_EXPLORERS entry missing id: %s" % entry.strip()[:80])
        if not (label and label.group(1)):
            fail("METRO_EXPLORERS[%s] missing label" % eid.group(1))
        if not (url and url.group(1).startswith("https://")):
            fail("METRO_EXPLORERS[%s] url missing or not https" % eid.group(1))
        ids.append(eid.group(1))

        bm = re.search(r"\bbbox:\s*\{([^}]*)\}", entry)
        if not bm:
            continue  # no bbox = the metro opts out of the portal; allowed
        vals = dict(re.findall(r"(minLng|minLat|maxLng|maxLat):\s*(-?[\d.]+)", bm.group(1)))
        if sorted(vals) != ["maxLat", "maxLng", "minLat", "minLng"]:
            fail("METRO_EXPLORERS[%s] bbox is missing fields (need minLng/minLat/maxLng/maxLat)" % eid.group(1))
        b = {k: float(v) for k, v in vals.items()}
        if not (b["minLat"] < b["maxLat"] and b["minLng"] < b["maxLng"]):
            fail("METRO_EXPLORERS[%s] bbox is inverted (min must be < max on both axes)" % eid.group(1))
        if eid.group(1) != this_metro and (
            b["minLat"] <= center_lat <= b["maxLat"] and b["minLng"] <= center_lng <= b["maxLng"]
        ):
            fail(
                "METRO_EXPLORERS[%s] bbox contains this metro's own center (%s, %s) — "
                "the metro-portal easter egg would fire on every pan at home" % (eid.group(1), center_lat, center_lng)
            )

    if len(set(ids)) != len(ids):
        fail("METRO_EXPLORERS has duplicate ids: %s" % ids)
    if this_metro not in ids:
        fail('METRO_EXPLORERS has no entry for THIS_METRO ("%s")' % this_metro)
    return len(ids)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "index.html"
    if not os.path.exists(path):
        fail("no such file: " + path)
    html = open(path).read()
    repo_root = os.path.dirname(os.path.abspath(path))
    app_dir = os.path.join(repo_root, "data", "app")

    # 0. ENGINE fences are structurally sound (docs/ENGINE_SYNC.md)
    check_engine_markers(html)

    # 0b. METRO_EXPLORERS config list is sane (metro-portal easter egg)
    n_metros = check_metro_explorers(html)

    # 0c. sw.js ENGINE fences are structurally sound too (the service worker's
    # handler logic is shared engine; docs/ENGINE_SYNC.md). Absence is reported
    # by check_sw_lists below with a clearer message.
    sw_path = os.path.join(repo_root, "sw.js")
    if os.path.exists(sw_path):
        check_engine_markers(open(sw_path).read())

    # 1. main inline script parses
    scripts = re.findall(r"<script>(.*?)</script>", html, re.DOTALL)
    if not scripts:
        fail("no inline <script> blocks found")
    main_script = max(scripts, key=len)
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as tf:
        tf.write(main_script)
        js_path = tf.name
    try:
        proc = subprocess.run(["node", "--check", js_path], capture_output=True, text=True)
    finally:
        os.unlink(js_path)
    if proc.returncode != 0:
        fail("inline script failed `node --check`:\n" + (proc.stderr or proc.stdout))

    # 2. no modules lost — engine floor plus every expected layer id present
    n = len(re.findall(r"registerLayer\(", html))
    if n < MIN_REGISTER_LAYER:
        fail("registerLayer( count %d < expected floor %d — a module was likely deleted" % (n, MIN_REGISTER_LAYER))
    for lid in EXPECT_LAYER_IDS:
        if ('id: "%s"' % lid) not in html:
            fail('layer id "%s" is not registered in index.html' % lid)

    # 2b. LAYER_AREA_RANK covers every registered id exactly once, and nothing
    # else (no "stub", no dropped layer). This is the z-order pass made
    # executable: reorderActiveLayers() walks this list, so a registered layer
    # missing here never gets restacked, and a stale id here is a silent no-op
    # that hides a rename.
    m = re.search(r"var LAYER_AREA_RANK = \[(.*?)\];", html, re.DOTALL)
    if not m:
        fail("LAYER_AREA_RANK array not found in index.html")
    rank = re.findall(r'"([a-z0-9-]+)"', m.group(1))
    dupes = sorted(set(x for x in rank if rank.count(x) > 1))
    if dupes:
        fail("LAYER_AREA_RANK lists these ids more than once: %s" % ", ".join(dupes))
    expected = set(EXPECT_LAYER_IDS)
    got = set(rank)
    missing = sorted(expected - got)
    extra = sorted(got - expected)
    if missing:
        fail("LAYER_AREA_RANK is missing registered layer id(s): %s" % ", ".join(missing))
    if extra:
        fail("LAYER_AREA_RANK has id(s) not in the registered set: %s" % ", ".join(extra))

    # 2c. LAYER_SIDEBAR_RANK covers every registered id exactly once, and
    # nothing else — same contract as 2b for the sidebar display order
    # (docs/EXPANSION_GUIDE.md Part 4 "Sidebar placement standard"): the boot
    # sort deliberately sinks an unranked id to the end instead of throwing,
    # so this check is the only place a rank/registry drift fails loudly.
    m = re.search(r"var LAYER_SIDEBAR_RANK = \[(.*?)\];", html, re.DOTALL)
    if not m:
        fail("LAYER_SIDEBAR_RANK array not found in index.html")
    srank = re.findall(r'"([a-z0-9-]+)"', m.group(1))
    dupes = sorted(set(x for x in srank if srank.count(x) > 1))
    if dupes:
        fail("LAYER_SIDEBAR_RANK lists these ids more than once: %s" % ", ".join(dupes))
    got = set(srank)
    missing = sorted(expected - got)
    extra = sorted(got - expected)
    if missing:
        fail("LAYER_SIDEBAR_RANK is missing registered layer id(s): %s" % ", ".join(missing))
    if extra:
        fail("LAYER_SIDEBAR_RANK has id(s) not in the registered set: %s" % ", ".join(extra))

    # 3. nothing embedded inline anymore, and every data file is referenced
    blobs = re.findall(r"var (\w+) = JSON\.parse\('", html)
    if blobs:
        fail("dataset(s) still embedded inline (should be in data/app/): %s" % blobs)
    for fname in list(GEOMETRY_FILES) + list(ROSTER_FILES):
        if fname in DYNAMIC_REFERENCE:
            continue  # URL built from a slug at runtime — see the generated set
        if ("data/app/" + fname) not in html:
            fail("index.html does not reference data/app/%s" % fname)

    # 4. every app-data file exists, parses, and has the right shape
    for fname, (lo, hi) in GEOMETRY_FILES.items():
        fpath = os.path.join(app_dir, fname)
        if not os.path.exists(fpath):
            fail("missing app-data file: data/app/%s" % fname)
        try:
            gj = json.load(open(fpath))
        except Exception as e:
            fail("data/app/%s does not parse as JSON: %s" % (fname, e))
        feats = gj.get("features") if isinstance(gj, dict) else None
        if gj.get("type") != "FeatureCollection" or not isinstance(feats, list):
            fail("data/app/%s is not a GeoJSON FeatureCollection" % fname)
        if not (lo <= len(feats) <= hi):
            fail("data/app/%s has %d features, expected %d-%d" % (fname, len(feats), lo, hi))

    for fname, min_keys in ROSTER_FILES.items():
        fpath = os.path.join(app_dir, fname)
        if not os.path.exists(fpath):
            fail("missing app-data file: data/app/%s" % fname)
        try:
            roster = json.load(open(fpath))
        except Exception as e:
            fail("data/app/%s does not parse as JSON: %s" % (fname, e))
        if not isinstance(roster, dict):
            fail("data/app/%s is not a JSON object" % fname)
        if len(roster) < min_keys:
            fail("data/app/%s has %d entries, expected at least %d" % (fname, len(roster), min_keys))

    # 5. sw.js exactly-one-list invariant: every data/app/*.json on disk
    # must be cached in exactly one of GEOMETRY_URLS (cache-first) or ROSTER_URLS
    # (network-first). A boundary served network-first would be a needless fetch;
    # a roster served cache-first could name a stale officeholder — the cardinal
    # sin here. An un-listed file silently loses offline support.
    # 4b. negative ground-truth point misses every anchor geometry
    check_negative_point(repo_root, app_dir)

    check_sw_lists(repo_root, app_dir)

    # 5. every county the app dispatches a layer on is inside the coverage ring
    n_counties = check_county_coverage_list(html, repo_root)

    # 5b. and the ring itself, which the check above cannot see here
    n_ring = check_coverage_ring_tracks_counties(repo_root, app_dir)

    # 6. the public sources page, if this fork ships one, still accounts for
    # every layer and is still reachable from the app.
    n_sourced = check_sources_page(html, repo_root)

    print(
        "validate_index: OK — inline script parses, %d registerLayer( calls, "
        "LAYER_AREA_RANK + LAYER_SIDEBAR_RANK cover all %d ids, no inline datasets, %d well-formed "
        "METRO_EXPLORERS entries, all data/app files present and cached in "
        "exactly one sw.js list, %d dispatched counties all inside the coverage "
        "ring whose %d counties match the shipped county layer exactly%s"
        % (n, len(EXPECT_LAYER_IDS), n_metros, n_counties, n_ring,
           "" if n_sourced is None else
           ", sources page linked and covering all %d layers" % n_sourced)
    )


SOURCES_PAGE = "sources.html"


def check_sources_page(html, repo_root):
    """The public sources page accounts for every registered layer, and the app
    still links to it. Returns the number of layers covered, or None if this
    fork ships no such page.

    Two failure modes, neither of which any other gate sees. A layer that ships
    without a matrix row leaves a reader reading the page as complete when it
    isn't — silence about a source reads as 'there is no source'. And a page
    nothing links to is a page nobody reads: the credits row that used to sit
    in the footer was self-evidently reachable, a separate page is only as
    reachable as its pointer. The row-per-layer content itself is generated
    from the same worksheet list as EXPECT_LAYER_IDS
    (scripts/generate_metro_files.py), so this checks the OUTCOME rather than
    trusting that the generator ran."""
    path = os.path.join(repo_root, SOURCES_PAGE)
    if not os.path.exists(path):
        return None
    page = open(path, encoding="utf-8").read()
    missing = [lid for lid in EXPECT_LAYER_IDS if ('id="layer-%s"' % lid) not in page]
    if missing:
        fail("%s has no matrix row for %d layer(s): %s — regenerate with "
             "scripts/generate_metro_files.py after adding the layer's source "
             "block to metro-worksheet.json"
             % (SOURCES_PAGE, len(missing), ", ".join(missing)))
    if SOURCES_PAGE not in html:
        fail("index.html no longer links to %s — the page ships but nothing in "
             "the app points a reader at it" % SOURCES_PAGE)
    return len(EXPECT_LAYER_IDS)


def _point_in_geometry(lng, lat, geom):
    """Stdlib ray-casting point-in-polygon over a GeoJSON (Multi)Polygon."""
    def ring_hit(ring):
        inside = False
        j = len(ring) - 1
        for i in range(len(ring)):
            xi, yi = ring[i][0], ring[i][1]
            xj, yj = ring[j][0], ring[j][1]
            if ((yi > lat) != (yj > lat)) and (lng < (xj - xi) * (lat - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        return inside
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    return any(ring_hit(p[0]) and not any(ring_hit(h) for h in p[1:]) for p in polys)


def check_negative_point(repo_root, app_dir):
    """4b. The worksheet's negative ground-truth point must miss EVERY feature
    of every anchor geometry file — the honest no-district state the smoke
    test asserts is only meaningful if the committed geometries agree. Catches
    a re-simplified boundary quietly swallowing the negative point."""
    ws_path = os.path.join(repo_root, "metro-worksheet.json")
    if not os.path.exists(ws_path):
        fail("metro-worksheet.json not found — negative-point ground truth needs it")
    ws = json.load(open(ws_path))
    neg = ws["negative_point"]
    lng, lat = neg["lng"], neg["lat"]
    for fname in GEOMETRY_FILES:
        gj = json.load(open(os.path.join(app_dir, fname)))
        for feat in gj.get("features", []):
            geom = feat.get("geometry") or {}
            if geom.get("type") not in ("Polygon", "MultiPolygon"):
                # amenity-point files (school-sites, library-sites) ride the
                # geometry list for their cache policy, but a point cannot
                # contain the negative point — nothing to assert here
                continue
            if _point_in_geometry(lng, lat, geom):
                fail(
                    "negative point %.5f,%.5f is INSIDE a feature of data/app/%s (%r) — "
                    "it must miss every anchor geometry; pick a new negative point in the "
                    "worksheet or check the geometry build" % (lat, lng, fname, feat.get("properties"))
                )


def _sw_url_list(sw, name):
    """Extract the ./data/app/*.json basenames from a `const NAME = [...]` array."""
    m = re.search(r"const %s = \[(.*?)\];" % name, sw, re.DOTALL)
    if not m:
        fail("sw.js: %s array not found" % name)
    return re.findall(r'\./data/app/([A-Za-z0-9._-]+\.json)', m.group(1))


def check_sw_lists(repo_root, app_dir):
    sw_path = os.path.join(repo_root, "sw.js")
    if not os.path.exists(sw_path):
        fail("sw.js not found next to index.html")
    sw = open(sw_path).read()
    geometry = _sw_url_list(sw, "GEOMETRY_URLS")
    roster = _sw_url_list(sw, "ROSTER_URLS")

    # No file appears in both lists.
    both = sorted(set(geometry) & set(roster))
    if both:
        fail("sw.js: file(s) in BOTH GEOMETRY_URLS and ROSTER_URLS: %s" % ", ".join(both))

    listed = geometry + roster
    dupes = sorted(set(x for x in listed if listed.count(x) > 1))
    if dupes:
        fail("sw.js: file(s) listed more than once: %s" % ", ".join(dupes))

    # Every listed file exists on disk.
    for fname in listed:
        if not os.path.exists(os.path.join(app_dir, fname)):
            fail("sw.js caches data/app/%s but the file does not exist" % fname)

    # Every data/app/*.json on disk is cached in exactly one list.
    on_disk = set(f for f in os.listdir(app_dir) if f.endswith(".json"))
    uncached = sorted(on_disk - set(listed))
    if uncached:
        fail("data/app file(s) not cached in any sw.js list: %s" % ", ".join(uncached))


# Layers that dispatch by MUNICIPALITY rather than by county. Their entry keys
# are place names, so they are exempt from the county check below. Listed, not
# inferred: a new municipality-keyed concept should have to say so here rather
# than quietly opting itself out of the guard.
MUNICIPALITY_KEYED_LAYERS = {"ward"}


# The distinctive word each county-dispatched layer's loader names carry. Used
# to catch an entry pasted into the wrong table: a loader that reads as another
# concept, and not as its own, is misfiled. Keys absent here are not checked.
LAYER_CONCEPT_TOKEN = {
    "county-board": "Board",
    "county-precinct": "Precinct",
    "fire-district": "Fire",
    "library-district": "Library",
    "park-district": "Park",
    "judicial-subcircuit": "Subcircuit",
}


def _literals_from(path, names):
    """Read module-level literals without importing the module.

    build_metro_outline.py imports `requests`, which is not installed in the
    smoke-test workflow where this gate runs — and executing a builder to read
    two constants would be the wrong trade anyway. ast parses, never runs.
    """
    import ast
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read(), path)
    found = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in names:
                try:
                    found[target.id] = ast.literal_eval(node.value)
                except ValueError:
                    pass
    missing = sorted(set(names) - set(found))
    if missing:
        fail("%s no longer defines %s — the county-list check cannot run"
             % (os.path.basename(path), ", ".join(missing)))
    return found


def check_county_coverage_list(html, repo_root):
    """Every county the app dispatches a layer on must be inside the scope mask.

    VACUOUS IN THIS INSTANCE, AND THAT IS WHY THE CHECK BELOW EXISTS. Michigan
    registers no registerCountyLayer dispatch entries at all — every county
    concept is one statewide layer — so this walks an empty set and returns 0
    on every run. It is kept because the shape is shared with the reference
    instance and a future dispatch entry must be covered from its first day,
    not because it is currently measuring anything.

    THE BUG IT EXISTS FOR, in an instance that does dispatch: the mask's county
    list was previously guarded only by the outline builder's OUTSIDE anchors,
    which catch a county only if somebody had already thought to name it. Four
    of the reference instance's counties therefore shipped layers and stayed
    greyed out for two research passes — the wash telling residents "beyond
    here only the statewide layers answer" while five of their layers answered.
    Nothing failed, because nothing was comparing the list against what the app
    actually registers. In Michigan that comparison is
    check_coverage_ring_tracks_counties(), below.

    So this derives the answer instead of trusting a list: it reads the county
    keys out of index.html's own dispatch tables and requires each one to be in
    METRO_COUNTY_FIPS. An unrecognised key fails too — a new county that nobody
    added to DISPATCH_COUNTY_FIPS is exactly the case that used to slip through.

    IT ALSO CHECKS THE REVERSE, which for a long time nothing did: a
    DISPATCH_COUNTY_FIPS row with no dispatch entry behind it. That gap was
    found on 2026-08-02 while shipping the at-large tier (Pike, Brown, Calhoun,
    Putnam) — counties served entirely through the COUNTY card, with no dispatch
    entry of any kind. The expansion guide had said to add such a county to
    DISPATCH_COUNTY_FIPS "if any other layer answers there", and adding one
    anyway passed every gate silently, because this function only ever looked
    from index.html outward. A stale row is not cosmetic: DISPATCH_COUNTY_FIPS
    is what build_county_outline.py cross-checks FIPS against and what the
    guidebook and CLAUDE.md quote as the count of dispatched counties, so a
    county listed there but dispatching nothing makes all three quietly wrong.
    An at-large county belongs in METRO_COUNTY_FIPS only.
    """
    outline_py = os.path.join(repo_root, "scripts", "build_metro_outline.py")
    if not os.path.exists(outline_py):
        fail("scripts/build_metro_outline.py not found — the county-list check "
             "cannot run; it is the source of the coverage ring")
    consts = _literals_from(outline_py, ("DISPATCH_COUNTY_FIPS", "METRO_COUNTY_FIPS"))
    slug_fips = consts["DISPATCH_COUNTY_FIPS"]
    in_ring = set(consts["METRO_COUNTY_FIPS"])

    # Split the script at every top-level register*() call so each dispatch
    # table is read within its own call and cannot absorb a neighbour's keys.
    chunks = re.split(r"\n  (register[A-Za-z]*)\(\{", html)
    unknown, outside, misfiled = [], [], []
    seen_counties = set()
    for i in range(1, len(chunks) - 1, 2):
        if chunks[i] != "registerCountyLayer":
            continue
        body = chunks[i + 1]
        layer_id = re.search(r'id:\s*"([a-z-]+)"', body)
        if not layer_id or layer_id.group(1) in MUNICIPALITY_KEYED_LAYERS:
            continue
        lid = layer_id.group(1)
        keys_here = re.findall(r'key:\s*"([a-z-]+)"', body)
        dupes = sorted({k for k in keys_here if keys_here.count(k) > 1})
        if dupes:
            fail("%s registers the same county key twice: %s. registerCountyLayer's "
                 "byKey lookup is LAST-WINS and render/cardIdentifier/primaryLink "
                 "all dispatch through it, so the duplicate silently re-points the "
                 "first entry's card at the second entry's renderer — no gate "
                 "notices, because the layer still registers and still queries."
                 % (lid, ", ".join(dupes)))
        # An entry whose loader belongs to a DIFFERENT concept is an entry pasted
        # into the wrong table. That shipped twice (2026-08-03/04): precinct
        # entries for Stephenson and Macon landed in county-board, which gave
        # Macon a board card it must not have and broke Stephenson's. The keys
        # were legal and unique, so nothing above caught it.
        own = LAYER_CONCEPT_TOKEN.get(lid)
        if own:
            others = {t for k, t in LAYER_CONCEPT_TOKEN.items() if t != own}
            for ekey, loader in re.findall(
                    r'key:\s*"([a-z-]+)",\s*\n\s*coverage:[^\n]*\n\s*'
                    r'(?:loadGeometry|loader):\s*(\w+)', body):
                foreign = sorted(t for t in others if t in loader)
                if foreign and own not in loader:
                    misfiled.append("%s entry '%s' uses %s (reads as %s, not %s)"
                                    % (lid, ekey, loader, "/".join(foreign), own))
        for key in keys_here:
            if key not in slug_fips:
                unknown.append("%s: %s" % (lid, key))
                continue
            seen_counties.add(key)
            if slug_fips[key] not in in_ring:
                outside.append("%s (%s)" % (key, lid))

    if misfiled:
        fail("dispatch entr%s sitting in the wrong layer's table: %s. Move the "
             "entry into the registerCountyLayer call for its own concept."
             % ("ies are" if len(misfiled) > 1 else "y is", "; ".join(sorted(misfiled))))
    if unknown:
        fail("dispatch entr%s for a county with no DISPATCH_COUNTY_FIPS entry: %s. "
             "Add the county (slug -> Census FIPS) to scripts/build_metro_outline.py, "
             "or list its layer in MUNICIPALITY_KEYED_LAYERS if it dispatches by "
             "place rather than county."
             % ("ies" if len(unknown) > 1 else "y", ", ".join(sorted(set(unknown)))))
    if outside:
        fail("county/counties serve layers but are NOT in METRO_COUNTY_FIPS, so the "
             "out-of-scope wash greys them out while their cards answer: %s. Add "
             "them to scripts/build_metro_outline.py and rebuild "
             "data/app/metro-outline.json."
             % ", ".join(sorted(set(outside))))

    # The reverse direction (see the docstring): listed as dispatched, but
    # dispatching nothing.
    undispatched = sorted(set(slug_fips) - seen_counties)
    if undispatched:
        fail("county/counties in DISPATCH_COUNTY_FIPS that register NO dispatch "
             "entry in index.html: %s. That list is the count of dispatched "
             "counties the docs quote and the FIPS table build_county_outline.py "
             "cross-checks, so a row with nothing behind it makes both wrong. If "
             "the county is served only through the COUNTY card (an AT-LARGE "
             "board — EXPANSION_GUIDE §3.5.1), remove it from DISPATCH_COUNTY_FIPS "
             "and leave it in METRO_COUNTY_FIPS. Otherwise its dispatch entry was "
             "dropped — restore it."
             % ", ".join(undispatched))
    return len(seen_counties)


def check_coverage_ring_tracks_counties(repo_root, app_dir):
    """METRO_COUNTY_FIPS must be exactly the counties this app answers for.

    THE CHECK ABOVE CANNOT SEE THIS INSTANCE. It walks registerCountyLayer
    dispatch entries, and Michigan has none — every concept it ships is ONE
    statewide layer, so DISPATCH_COUNTY_FIPS is empty by design, that loop
    never executes, and it would report "0 dispatched counties all inside the
    coverage ring" on every run: a vacuum printed as a result. Wisconsin, the
    same shape, closed this after seven counties sat greyed out for two days
    with every gate in the repo green; Iowa carried the identical hole.

    WHICH FILE IS THE COMPARAND MATTERS, and for Michigan it is not a roster.
    Iowa holds its ring to ia-county-officers.json, the roster that must answer
    everywhere its wash reaches. This instance ships NO county roster at all —
    the county card is identity-only until the commissioner-district layer
    lands — so the file that enumerates the counties this app actually answers
    for is the county GEOMETRY itself. Holding the ring to state-counties.json
    is the same claim in the shape this instance has: the wash may not grey out
    a county whose card answers, and may not promise one the app cannot draw.
    When the commissioner roster ships, it becomes the stricter comparand and
    this check should move to it.
    """
    outline_py = os.path.join(repo_root, "scripts", "build_metro_outline.py")
    counties_path = os.path.join(app_dir, "state-counties.json")
    for path in (outline_py, counties_path):
        if not os.path.exists(path):
            fail("%s not found — the coverage-ring/county check cannot run"
                 % os.path.relpath(path, repo_root))
            return 0

    in_ring = set(_literals_from(outline_py, ("METRO_COUNTY_FIPS",))["METRO_COUNTY_FIPS"])
    with open(counties_path, encoding="utf-8") as f:
        counties = json.load(f)
    features = counties.get("features") or []
    # GEOID is 5 digits ("26001"), the ring is the 3-digit county code ("001").
    # Sliced rather than stripped of a literal "26" so a malformed key cannot
    # silently normalise to something plausible.
    drawn, malformed = set(), []
    for feat in features:
        props = feat.get("properties") or {}
        geoid = str(props.get("GEOID") or props.get("geoid") or "")
        if len(geoid) != 5 or not geoid.isdigit():
            malformed.append(geoid or "<missing>")
            continue
        drawn.add(geoid[-3:])
    if malformed:
        fail("state-counties.json has %d feature(s) whose GEOID is not 5 digits "
             "(%s) — the ring cannot be compared against keys it cannot read"
             % (len(malformed), ", ".join(malformed[:6])))
        return 0

    masked = sorted(drawn - in_ring)
    if masked:
        fail("count%s this app DRAWS but which sit outside METRO_COUNTY_FIPS, so "
             "the out-of-scope wash greys them out while their cards answer in "
             "full: %s. Add the FIPS to mi/scripts/build_metro_outline.py WITH an "
             "INSIDE anchor and rebuild data/app/metro-outline.json."
             % ("ies" if len(masked) > 1 else "y", ", ".join(masked)))
    promised = sorted(in_ring - drawn)
    if promised:
        fail("count%s inside METRO_COUNTY_FIPS with no feature in "
             "state-counties.json, so the wash promises an answer the map cannot "
             "draw: %s. Either the county layer stopped resolving (rebuild it) or "
             "the county was added to the ring too early."
             % ("ies are" if len(promised) > 1 else "y is", ", ".join(promised)))
    return len(in_ring)


if __name__ == "__main__":
    main()
