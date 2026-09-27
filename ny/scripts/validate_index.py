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
  2. registerLayer( appears at least as many times as expected.
  3. index.html embeds no dataset inline (no `JSON.parse('...')` blobs remain)
     and references each data/app/* file it fetches.
  4. Every expected data/app/*.json exists, parses, and has the right shape.
  5. LAYER_AREA_RANK lists every registered layer id exactly once and nothing
     else — the z-order honesty rule (§3/§7) made executable so a layer can
     never be registered but forgotten in the stack (or vice versa).
  6. sw.js exactly-one-list invariant (§4): every data/app/*.json on disk is
     cached in exactly one of the service worker's GEOMETRY_URLS / ROSTER_URLS,
     so no data file is ever un-cached or double-listed.
  7. METRO_EXPLORERS entries are well formed (id/label/https url; bbox, when
     present, is a sane min<max box that does NOT contain this metro's own
     center — a bbox covering home would make the sibling-metro portal easter
     egg fire on every pan). Guards the copy-verbatim config diff every fork
     applies when a new metro launches.

Usage:
    python3 scripts/validate_index.py [path/to/index.html]
"""

import json
import os
import re
import subprocess
import sys
import tempfile

# Machine-readable capability declaration (CHI docs/MECHANIZATION_PLAYBOOK.md,
# Conversion 3). The fleet-status workflow in the CHI repo parses this list
# from every fork's validator and diffs it against CHI's: a capability present
# in a fork but absent in CHI is a reverse-parity WARN — the mechanical form
# of "fork-born validator improvements must land in CHI within one release
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
    "no-inline-datasets",       # 3: no JSON.parse blobs; data files referenced
    "data-file-shapes",         # 4: every data/app file exists with sane counts
    "sw-exactly-one-list",      # 5: each data file cached in exactly one sw list
    "negative-point-ground-truth",  # 4b: worksheet negative point misses every anchor geometry (born here; CHI back-port pending)
]

# The constants below are GENERATED from metro-worksheet.json (Conversion 2 —
# edit the worksheet, run scripts/generate_metro_files.py). Fork history worth
# keeping by hand: NYC's registerLayer floor arithmetic is 1 function
# definition + 4 factory bodies (registerPolygonLayer / registerSchoolZone /
# registerCpsNetwork / registerIlgaChamber) — NYC modules all register through
# factories, so module loss is guarded by EXPECT_LAYER_IDS, not this count.
# ==== GENERATED:BEGIN validator-config ====
# Floor, not a moving target: new layers only raise this; a drop means
# modules were lost.
MIN_REGISTER_LAYER = 5

# Every layer id that must be registered in index.html. Most modules register
# through the factories, so deleting one would NOT lower the raw registerLayer(
# count above — this per-id list is the direct module-loss guard. Emitted in
# LAYER_AREA_RANK order; check 5 keeps the two naming the same set.
EXPECT_LAYER_IDS = [
    "judicial-district", "county", "nys-central-hs-district",
    "nys-school-district", "municipality", "county-legislature", "village",
    "borough", "borough-president", "district-attorney", "congress",
    "municipal-court", "state-senate", "school-district", "cec",
    "fire-battalion", "council", "community-district", "election-district",
    "state-assembly", "police-sector", "police-precinct", "nys-zip-code",
    "zip-code", "neighborhood", "hs-zone", "ms-zone", "es-zone",
    "school-site", "police-station", "fire-station", "post-office", "library",
    "early-voting", "polling-place",
]

# file -> (min features, max features) for the boundary layers fetched by the app.
GEOMETRY_FILES = {
    "metro-outline.json": (1, 1),  # The dissolved outline of the five boroughs, the coverage wash's FULL band (ny/scripts/build_metro_outline.py, anchor-verified inside and outside). Three rings, not one: the borough cluster plus Liberty Island and Ellis Island, both New York County land detached by water.
    "ny-state-outline.json": (1, 1),  # New York State, the coverage wash's REGION band, marking where the three statewide legislative layers answer although the city layers do not. Same builder, same simplification tolerance as the coverage ring so the two do not open slivers where they trace the same line.
    "borough-boundaries.json": (5, 5),
    "bronx-county-outline.json": (1, 1),  # The Bronx containment outline (ny/scripts/build_ny_borough_outlines.py, sliced from borough-boundaries.json) — lets a Data gaps record name this borough so the panel leads with the gaps that apply here.
    "brooklyn-county-outline.json": (1, 1),  # Brooklyn containment outline (ny/scripts/build_ny_borough_outlines.py, sliced from borough-boundaries.json) — lets a Data gaps record name this borough so the panel leads with the gaps that apply here.
    "manhattan-county-outline.json": (1, 1),  # Manhattan containment outline (ny/scripts/build_ny_borough_outlines.py, sliced from borough-boundaries.json) — lets a Data gaps record name this borough so the panel leads with the gaps that apply here.
    "queens-county-outline.json": (1, 1),  # Queens containment outline (ny/scripts/build_ny_borough_outlines.py, sliced from borough-boundaries.json) — lets a Data gaps record name this borough so the panel leads with the gaps that apply here.
    "staten-island-county-outline.json": (1, 1),  # Staten Island containment outline (ny/scripts/build_ny_borough_outlines.py, sliced from borough-boundaries.json) — lets a Data gaps record name this borough so the panel leads with the gaps that apply here.
    "judicial-districts.json": (13, 13),  # All thirteen New York judicial districts, dissolved from the SHIPPED ny-counties.json on the Judiciary Law section 140 table by ny/scripts/build_ny_judicial_districts.py, with no further simplification -- so every vertex here is a vertex of that file and the two layers draw one line rather than two. Rebuild it after ny-counties.json; validate_index.py fails the merge if they stop sharing vertices. Replaces the five-borough crosswalk file.
    "ny-counties.json": (62, 62),  # New York's 62 counties from the state's own Civil Boundaries service, carrying the NYC flag that marks the five counties with no county government. Built with the town and village layers in ONE mapshaper run (ny/scripts/build_ny_civil_boundaries.py), because the county layer is the publisher's own dissolve of the town layer -- 98.4% of its source vertices ARE town vertices -- and three separate runs drew the shared line up to 310 m apart. Shoreline-clipped, so it disagrees with the water-inclusive coverage ring at the coast by design.
    "ny-school-districts.json": (713, 713),  # The ORDINARY tier: 713 of the 716 school districts dissolved from the state's 936 polygon rows on SED_CODE_1 (ny/scripts/build_ny_school_districts.py). The 936 against the Census Bureau's 680 reconciles exactly: 33 New York City rows, 220 multipart and duplicate-code rows, 3 special-act districts. The other 3 are the central high school districts, split into their own file because no point resolved to them while they sat behind their own components in this one; measured 2026-09-26, these 713 have ZERO overlapping pairs under an exhaustive sweep.
    "ny-central-hs-districts.json": (3, 3),  # The UPPER tier: the three central high school districts, each entirely made of its component districts (Bellmore-Merrick, Sewanhaka Central, Valley Stream Central), split out by containment because nothing the state publishes marks the tier — two carry a blank SED code and the third carries its own component's. Mutually disjoint, measured 2026-09-26.
    "ny-cities-towns.json": (995, 995),  # New York's 62 cities and 933 towns, which together tile the state. One of the three layers ny/scripts/build_ny_civil_boundaries.py simplifies in a single shared topology with Douglas-Peucker at a 25 m interval.
    "ny-villages.json": (532, 532),  # New York's 532 villages, which sit INSIDE towns rather than beside them, so this is a nested layer and not part of the tiling. The state draws it independently of the town layer (9 of 145,280 source vertices are shared), so a shared topology cannot align the seven coterminous town/village governments and the 25 m Douglas-Peucker interval is what bounds them: measured 2026-09-26, six of the seven went from 78-320 m apart to 16-26 m, against the publisher's own 1 m. Woodbury's 1,484 m disagreement is the publisher's and ships as measured.
    "municipal-court-districts.json": (28, 28),
    "congress-districts.json": (26, 26),  # 26 NY U.S. House districts; pre-built from TIGERweb by scripts/build_legislative_boundaries.py (R2-2)
    "state-senate-districts.json": (63, 63),  # 63 NY State Senate districts; pre-built from TIGERweb layer 1
    "state-assembly-districts.json": (150, 150),  # 150 NY State Assembly districts; pre-built from TIGERweb layer 2
    "tompkins-legislature-districts.json": (16, 16),  # Tompkins County's 16 county-legislature districts (ny/scripts/build_tompkins_legislature.py), the county's own GIS simplified with Douglas-Peucker at a 25 m interval — the same interval the county fabric ships at, because the districts' outer edge is the county line. The bounds are EXACT rather than a floor: the county elects one legislator per district and that count cannot move between censuses.
    "tompkins-county-outline.json": (1, 1),  # Tompkins County sliced verbatim from ny-counties.json, so the county-legislature layer's coverage test and the county card cannot disagree about where Tompkins is — and what a Data gaps record needs in order to name this county.
}

# file -> minimum key count (officeholder rosters).
ROSTER_FILES = {
    "nypd-precinct-info.json": 70,  # keys every precinct (even a null CO), so the floor is the precinct count, not the commander count
    "congress-roster.json": 26,
    "coverage-gaps.json": 3,  # Known data gaps keyed by gap id, driving the Data gaps panel — emitted from the fleet guidebook's GUIDEBOOK:BEGIN gaps block by scripts/build_coverage_gaps.py, which reads this fork's this_metro key (--check is the drift gate). Network-first like the rosters: a closed gap should stop being advertised on the next visit.
    "council-members.json": 48,
    "ny-senate-members.json": 60,
    "ny-assembly-members.json": 145,
    "cec-members.json": 0,  # honest placeholder (floor 0): CEC members are decentralized across 32 independent council sites with no scrapable central source or Open Data dataset; card links to the DOE hub (see scripts/cec_scraper.py)
    "borough-officials.json": 5,  # 10 offices (5 BP + 5 DA), operator-maintained from official sites; floor 5 = one entry per borough (build_borough_officials.py keys by borough)
    "tompkins-legislature-members.json": 17,  # The 16 legislators keyed by district plus one `board` key carrying the Legislature's own office, switchboard, fax and term — so 17 keys, not 16. People from the county's own Legislature page and contact sheet, never from the boundary layer's own member column.
}

# Files the app references DYNAMICALLY — the URL is built from a slug at
# runtime (the gaps panel's <slug>-county-outline.json contract), so no
# literal appears in index.html. Exempt from the reference check only;
# existence, shape and the negative-point test still apply.
DYNAMIC_REFERENCE = frozenset({
    "bronx-county-outline.json",
    "brooklyn-county-outline.json",
    "manhattan-county-outline.json",
    "queens-county-outline.json",
    "staten-island-county-outline.json",
    "tompkins-county-outline.json",
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



def check_school_district_tiers(app_dir):
    """The two school-district tiers must stay a PARTITION of one source.

    New York's central high school districts ship in their own file because no
    point resolved to them while they sat behind their own components in the
    statewide file (findFeatureContaining takes the FIRST containing feature in
    file order). The split is derived by containment in
    ny/scripts/build_ny_school_districts.py, so two things have to keep holding
    and neither is checked by the feature counts above: no district may appear in
    both files, and the upper tier must be exactly the districts that contain
    others.

    This is the cheap half — set arithmetic on the names, offline and stdlib.
    The geometric half (each upper district ~entirely covered by its components,
    the two tiers internally disjoint) is the builder's own `--check`, which
    re-splits the shipped geometry and compares bytes.
    """
    lower = os.path.join(app_dir, "ny-school-districts.json")
    upper = os.path.join(app_dir, "ny-central-hs-districts.json")
    for path in (lower, upper):
        if not os.path.exists(path):
            fail("school-district tiers: %s is missing" % os.path.basename(path))

    def names(path):
        feats = json.load(open(path))["features"]
        return [f.get("properties", {}).get("SCHOOLDIST") for f in feats]

    lo, up = names(lower), names(upper)
    both = sorted(set(n for n in lo if n in set(up)))
    if both:
        fail("school-district tiers: %d district(s) appear in BOTH files (%s) "
             "— the tiers must partition the source, or one point answers twice"
             % (len(both), ", ".join(str(b) for b in both[:5])))
    if len(set(up)) != len(up):
        fail("school-district tiers: the upper tier repeats a district name (%r)"
             % (up,))
    if not up:
        fail("school-district tiers: the upper-tier file is empty — the three "
             "central high school districts would answer nobody again")


def check_shared_civil_edges(app_dir):
    """The layers that share a line must still SHARE ITS VERTICES.

    New York's county layer is the publisher's own dissolve of its town layer --
    measured 2026-09-26, 98.4% of county vertices at source ARE town vertices --
    and its 13 judicial districts are unions of whole counties. So a shared edge
    is one line, and under one mapshaper topology it is one arc simplified once,
    which makes the SAME vertices appear in both files. That is what this checks,
    and it needs no source, no network and no geometry library: set arithmetic on
    the coordinates.

    It is the cheap half. The geometric half -- how far each drawn line strays
    from the publisher's own, and that the two built layers agree to 0.0 m on
    every stretch the publisher draws once -- needs the 28 MB fetch and is
    ny/scripts/build_ny_civil_boundaries.py's own gate at build time.

    WHY IT IS WORTH A MERGE GATE: the tree that shipped until 2026-09-26 built
    these three files in three separate mapshaper runs, which cannot produce one
    shared arc, and only 52.2% of county vertices were still town vertices while
    the two files drew the same line up to 310 m apart. Every other gate in this
    file was green on that tree, including the 2,000-point classification, which
    cannot see WHERE a line is. The judicial file missed by exactly one vertex,
    which is the kind of margin only an exact test finds.
    """
    counties = os.path.join(app_dir, "ny-counties.json")
    towns = os.path.join(app_dir, "ny-cities-towns.json")
    judicial = os.path.join(app_dir, "judicial-districts.json")
    for path in (counties, towns, judicial):
        if not os.path.exists(path):
            fail("shared civil edges: %s is missing" % os.path.basename(path))

    def verts(path):
        out = set()
        for f in json.load(open(path))["features"]:
            geom = f.get("geometry")
            if not geom:
                continue

            def walk(c):
                if c and isinstance(c[0], (int, float)):
                    out.add((c[0], c[1]))
                else:
                    for x in c:
                        walk(x)

            walk(geom["coordinates"])
        return out

    cv, tv, jv = verts(counties), verts(towns), verts(judicial)
    if not cv or not tv or not jv:
        fail("shared civil edges: one of the three files carries no vertices")

    # The five boroughs' mutual boundaries exist in the county layer and in no
    # town (New York City is ONE row of the town layer), so the county share is
    # a floor near the source's own 98.4% rather than 100%.
    share = 100.0 * len(cv & tv) / len(cv)
    if share < 97.0:
        fail("shared civil edges: only %.2f%% of ny-counties.json's %d vertices are "
             "also vertices of ny-cities-towns.json (floor 97.0%%, the source's own "
             "figure is 98.4%%, three separate mapshaper runs gave 52.2%%) — rebuild "
             "both with ny/scripts/build_ny_civil_boundaries.py, which simplifies "
             "them in ONE run" % (share, len(cv)))

    # A judicial district is a dissolve of the SHIPPED counties with no further
    # simplification, so this one is exact with no tolerance.
    stray = jv - cv
    if stray:
        fail("shared civil edges: %d of judicial-districts.json's %d vertices are not "
             "vertices of ny-counties.json (e.g. %r) — rebuild it with "
             "ny/scripts/build_ny_judicial_districts.py AFTER ny-counties.json, which "
             "it dissolves" % (len(stray), len(jv), sorted(stray)[:2]))


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "index.html"
    if not os.path.exists(path):
        fail("no such file: " + path)
    html = open(path).read()
    repo_root = os.path.dirname(os.path.abspath(path))
    app_dir = os.path.join(repo_root, "data", "app")

    # 0. ENGINE fences are structurally sound (docs/ENGINE_SYNC.md)
    check_engine_markers(html)

    # 0a. the two school-district tiers still partition one source
    check_school_district_tiers(os.path.join(os.path.dirname(os.path.abspath(path)), "data", "app"))

    # 0a2. the layers that share a line still share its vertices
    check_shared_civil_edges(app_dir)

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
        fail("registerLayer( count %d < expected floor %d — the engine/factories were likely damaged" % (n, MIN_REGISTER_LAYER))
    for lid in EXPECT_LAYER_IDS:
        if ('id: "%s"' % lid) not in html:
            fail('layer id "%s" is not registered in index.html' % lid)

    # 2b. LAYER_AREA_RANK covers every registered id exactly once, and nothing
    # else (no "stub", no dropped layer). This is the z-order "final visual
    # pass" (§7) made executable: reorderActiveLayers() walks this list, so a
    # registered layer missing here never gets restacked, and a stale id here
    # is a silent no-op that hides a rename.
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

    # 5. sw.js exactly-one-list invariant (§4): every data/app/*.json on disk
    # must be cached in exactly one of GEOMETRY_URLS (cache-first) or ROSTER_URLS
    # (network-first). A boundary served network-first would be a needless fetch;
    # a roster served cache-first could name a stale officeholder — the cardinal
    # sin here. An un-listed file silently loses offline support.
    # 4b. negative ground-truth point misses every anchor geometry
    check_negative_point(repo_root, app_dir)

    check_sw_lists(repo_root, app_dir)

    # 5. the public sources page, if this instance ships one, still accounts
    # for every layer and is still reachable from the app.
    n_sourced = check_sources_page(html, repo_root)

    print(
        "validate_index: OK — inline script parses, %d registerLayer( calls, "
        "LAYER_AREA_RANK covers all %d ids, no inline datasets, %d well-formed "
        "METRO_EXPLORERS entries, all data/app files present and cached in "
        "exactly one sw.js list%s"
        % (n, len(EXPECT_LAYER_IDS), n_metros,
           "" if n_sourced is None else
           ", sources page linked and covering all %d layers" % n_sourced)
    )


SOURCES_PAGE = "sources.html"


def check_sources_page(html, repo_root):
    """The public sources page accounts for every registered layer, and the app
    still links to it. Returns the number of layers covered, or None if this
    instance ships no such page.

    PORTED FROM THE REFERENCE INSTANCE 2026-09-02, WHICH IS THE POINT: this
    instance shipped a sources.html with a full matrix, linked from index.html,
    and its validator had no check for either — the reference instance,
    Wisconsin and Iowa all had one. So two of five instances published a
    provenance page that nothing gated: a layer could ship there with no row,
    or the link could be removed, with every gate green.

    Two failure modes, neither of which any other gate sees. A layer that ships
    without a matrix row leaves a reader reading the page as complete when it
    isn't — silence about a source reads as "there is no source". And a page
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
             "block to the worksheet"
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
            if _point_in_geometry(lng, lat, feat["geometry"]):
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


if __name__ == "__main__":
    main()
