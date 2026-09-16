#!/usr/bin/env python3
"""
Emit docs/COUNTY_STATUS.md — the standing per-county completion view.

Why this exists: "is county X complete?" had no single place to look. The
answer was spread over three artifacts, each individually gated but never
joined — the coverage-ring lists in scripts/build_metro_outline.py (which
counties are served, and how), index.html's own dispatch tables (which
concepts answer in each), and the guidebook's gaps block via
data/app/coverage-gaps.json (what is known to be missing, and why). Every
prose count of those things goes stale by design (CLAUDE.md's own coverage
sentence disclaims itself); this file is the join, regenerated instead of
maintained, so it cannot rot the way prose does.

Everything here is DERIVED — the only data this script owns is the static
list of all 102 Illinois counties (name + Census FIPS), which changes on a
constitutional timescale. Tiers are computed, never asserted:

    dispatch    = the slugs of DISPATCH_COUNTY_FIPS (cross-checked below)
    County card = counties in data/app/il-county-commissioners.json with no
                  dispatch entry (the at-large tier)
    judicial    = the remainder of METRO_COUNTY_FIPS (secondary counties of
                  shipped judicial circuits)
    frontier    = named by a gap record but outside the coverage ring
    unresearched= the rest of the 102

The dispatch-table scan is the same split-and-key read as
scripts/validate_index.py check_county_coverage_list — KEEP THEM IN LOCKSTEP.
If they ever disagree, the cross-assert here (scanned counties must equal
DISPATCH_COUNTY_FIPS exactly, the invariant that check enforces) fails loudly
rather than printing a wrong table.

`--check` re-emits and byte-compares, wired into smoke-test.yml next to
build_coverage_gaps.py --check: a county change that skips the regenerate
fails CI. Stdlib only, so it runs before anything is installed.

Usage:
    python3 scripts/build_county_status.py            # write docs/COUNTY_STATUS.md
    python3 scripts/build_county_status.py --check    # verify, write nothing
"""

import argparse
import glob
import ast
import json
import os
import re
import sys
from scraper_common import make_fail  # noqa: E402  (shared machinery — do not fork)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTLINE_PY = os.path.join(REPO_ROOT, "scripts", "build_metro_outline.py")
VALIDATE_PY = os.path.join(REPO_ROOT, "scripts", "validate_index.py")
INDEX_HTML = os.path.join(REPO_ROOT, "il", "index.html")
GAPS_JSON = os.path.join(REPO_ROOT, "il", "data", "app", "coverage-gaps.json")
OUT_PATH = os.path.join(REPO_ROOT, "docs", "COUNTY_STATUS.md")
STATS_PATH = os.path.join(REPO_ROOT, "stats.json")

# ==== TEMPLATE:BEGIN county-status-config ====
COMMISSIONERS_JSON = os.path.join(REPO_ROOT, "il", "data", "app",
                                  "il-county-commissioners.json")
STATE_FIPS = "17"

# All 102 Illinois counties, name -> county FIPS. Static on purpose: this is
# the denominator of every "N of 102" claim, and it is the one input no other
# artifact carries. 42 of the pairs are cross-checked against
# DISPATCH_COUNTY_FIPS below and ten more against the tier derivation, so a
# typo in a served county cannot survive a run.
ALL_COUNTIES = (
    ("Adams", "001"), ("Alexander", "003"), ("Bond", "005"), ("Boone", "007"),
    ("Brown", "009"), ("Bureau", "011"), ("Calhoun", "013"), ("Carroll", "015"),
    ("Cass", "017"), ("Champaign", "019"), ("Christian", "021"), ("Clark", "023"),
    ("Clay", "025"), ("Clinton", "027"), ("Coles", "029"), ("Cook", "031"),
    ("Crawford", "033"), ("Cumberland", "035"), ("DeKalb", "037"), ("De Witt", "039"),
    ("Douglas", "041"), ("DuPage", "043"), ("Edgar", "045"), ("Edwards", "047"),
    ("Effingham", "049"), ("Fayette", "051"), ("Ford", "053"), ("Franklin", "055"),
    ("Fulton", "057"), ("Gallatin", "059"), ("Greene", "061"), ("Grundy", "063"),
    ("Hamilton", "065"), ("Hancock", "067"), ("Hardin", "069"), ("Henderson", "071"),
    ("Henry", "073"), ("Iroquois", "075"), ("Jackson", "077"), ("Jasper", "079"),
    ("Jefferson", "081"), ("Jersey", "083"), ("Jo Daviess", "085"), ("Johnson", "087"),
    ("Kane", "089"), ("Kankakee", "091"), ("Kendall", "093"), ("Knox", "095"),
    ("Lake", "097"), ("LaSalle", "099"), ("Lawrence", "101"), ("Lee", "103"),
    ("Livingston", "105"), ("Logan", "107"), ("McDonough", "109"), ("McHenry", "111"),
    ("McLean", "113"), ("Macon", "115"), ("Macoupin", "117"), ("Madison", "119"),
    ("Marion", "121"), ("Marshall", "123"), ("Mason", "125"), ("Massac", "127"),
    ("Menard", "129"), ("Mercer", "131"), ("Monroe", "133"), ("Montgomery", "135"),
    ("Morgan", "137"), ("Moultrie", "139"), ("Ogle", "141"), ("Peoria", "143"),
    ("Perry", "145"), ("Piatt", "147"), ("Pike", "149"), ("Pope", "151"),
    ("Pulaski", "153"), ("Putnam", "155"), ("Randolph", "157"), ("Richland", "159"),
    ("Rock Island", "161"), ("St. Clair", "163"), ("Saline", "165"), ("Sangamon", "167"),
    ("Schuyler", "169"), ("Scott", "171"), ("Shelby", "173"), ("Stark", "175"),
    ("Stephenson", "177"), ("Tazewell", "179"), ("Union", "181"), ("Vermilion", "183"),
    ("Wabash", "185"), ("Warren", "187"), ("Washington", "189"), ("Wayne", "191"),
    ("White", "193"), ("Whiteside", "195"), ("Will", "197"), ("Williamson", "199"),
    ("Winnebago", "201"), ("Woodford", "203"),
)

# The repo's slug convention is the default rule below except where it isn't:
# "De Witt" ships as "dewitt" everywhere (dispatch table, outline file, gaps).
SLUG_OVERRIDES = {"De Witt": "dewitt"}
# ==== TEMPLATE:END county-status-config ====


fail = make_fail("build-county-status")


def slug_of(name):
    if name in SLUG_OVERRIDES:
        return SLUG_OVERRIDES[name]
    return name.lower().replace(".", "").replace(" ", "-")


def literals_from(path, names):
    """ast-read module constants without importing (build_metro_outline.py
    imports requests, which CI does not install for this gate — same approach
    and same reason as validate_index.py's _literals_from)."""
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
        fail("%s no longer defines %s" % (os.path.basename(path), ", ".join(missing)))
    return found


def scan_dispatch_tables(html, skip_layers):
    """layer id -> sorted county slugs, from index.html's registerCountyLayer
    tables. Same split and key regexes as validate_index.py
    check_county_coverage_list — keep in lockstep (the cross-assert in main()
    catches divergence)."""
    chunks = re.split(r"\n  (register[A-Za-z]*)\(\{", html)
    by_layer = {}
    for i in range(1, len(chunks) - 1, 2):
        if chunks[i] != "registerCountyLayer":
            continue
        body = chunks[i + 1]
        layer_id = re.search(r'id:\s*"([a-z-]+)"', body)
        if not layer_id or layer_id.group(1) in skip_layers:
            continue
        keys = re.findall(r'key:\s*"([a-z-]+)"', body)
        by_layer.setdefault(layer_id.group(1), set()).update(keys)
    return {layer: sorted(keys) for layer, keys in by_layer.items()}


def load_inputs():
    consts = literals_from(OUTLINE_PY, ("DISPATCH_COUNTY_FIPS", "METRO_COUNTY_FIPS"))
    skip = literals_from(VALIDATE_PY, ("MUNICIPALITY_KEYED_LAYERS",))[
        "MUNICIPALITY_KEYED_LAYERS"]
    with open(INDEX_HTML, encoding="utf-8") as f:
        dispatch_tables = scan_dispatch_tables(f.read(), skip)
    with open(GAPS_JSON, encoding="utf-8") as f:
        gaps = json.load(f)
    with open(COMMISSIONERS_JSON, encoding="utf-8") as f:
        commissioners = json.load(f)
    return consts, dispatch_tables, gaps, commissioners


def derive(consts, dispatch_tables, gaps, commissioners):
    fips_by_slug = {slug_of(n): f for n, f in ALL_COUNTIES}
    name_by_slug = {slug_of(n): n for n, f in ALL_COUNTIES}
    slug_by_fips = {f: slug_of(n) for n, f in ALL_COUNTIES}

    # The static list has to be internally sound before anything trusts it.
    if len(ALL_COUNTIES) != 102 or len(fips_by_slug) != 102 or len(slug_by_fips) != 102:
        fail("ALL_COUNTIES must hold 102 unique names and unique FIPS")
    expected = ["%03d" % n for n in range(1, 204, 2)]
    if sorted(f for _, f in ALL_COUNTIES) != expected:
        fail("ALL_COUNTIES FIPS must be exactly the odd codes 001..203")

    dispatch = consts["DISPATCH_COUNTY_FIPS"]
    ring = set(consts["METRO_COUNTY_FIPS"])
    # Cross-check the static list against the repo's own slug->FIPS table.
    for slug, fips in sorted(dispatch.items()):
        if fips_by_slug.get(slug) != fips:
            fail("ALL_COUNTIES disagrees with DISPATCH_COUNTY_FIPS on %r "
                 "(%s vs %s)" % (slug, fips_by_slug.get(slug), fips))
    unknown_ring = sorted(ring - set(slug_by_fips))
    if unknown_ring:
        fail("METRO_COUNTY_FIPS names FIPS not in ALL_COUNTIES: %s" % unknown_ring)

    # Same invariant validate_index.py check 8 enforces; if the scan and that
    # check ever read the tables differently, this is where it surfaces.
    scanned = set()
    for keys in dispatch_tables.values():
        scanned.update(keys)
    if scanned != set(dispatch):
        fail("dispatch-table scan disagrees with DISPATCH_COUNTY_FIPS "
             "(scan-only: %s; list-only: %s) — this script's scanner has "
             "drifted from validate_index.py check_county_coverage_list"
             % (sorted(scanned - set(dispatch)), sorted(set(dispatch) - scanned)))

    # At-large counties: keyed by shouting name in the commissioners file.
    atlarge_slugs = set()
    for key in commissioners:
        matches = [s for s in fips_by_slug
                   if name_by_slug[s].upper().replace(".", "").replace(" ", "")
                   == key.replace(".", "").replace(" ", "")]
        if len(matches) != 1:
            fail("commissioners key %r matches %d counties" % (key, len(matches)))
        atlarge_slugs.add(matches[0])

    dispatch_slugs = set(dispatch)
    card_only = atlarge_slugs - dispatch_slugs
    judicial = {slug_by_fips[f] for f in ring} - dispatch_slugs - card_only
    served = dispatch_slugs | card_only | judicial
    if {fips_by_slug[s] for s in served} != ring:
        fail("derived served set does not reproduce METRO_COUNTY_FIPS")

    # Gap records per county. A record may name several counties (it appears
    # in each row) or none (listed separately so totals still reconcile).
    gaps_by_county, untagged = {}, []
    for gap_id in sorted(gaps):
        counties = gaps[gap_id].get("counties") or []
        if not counties:
            untagged.append(gap_id)
        for slug in counties:
            if slug not in fips_by_slug:
                fail("gap %r names unknown county slug %r" % (gap_id, slug))
            gaps_by_county.setdefault(slug, []).append(gap_id)

    frontier = set(gaps_by_county) - served
    unresearched = set(fips_by_slug) - served - frontier
    layers_by_county = {}
    for layer, keys in dispatch_tables.items():
        for slug in keys:
            layers_by_county.setdefault(slug, []).append(layer)

    return {
        "name_by_slug": name_by_slug, "fips_by_slug": fips_by_slug,
        "dispatch": dispatch_slugs, "card_only": card_only,
        "judicial": judicial, "served": served, "frontier": frontier,
        "unresearched": unresearched, "atlarge": atlarge_slugs,
        "gaps_by_county": gaps_by_county, "untagged": untagged,
        "layers_by_county": layers_by_county, "gaps": gaps,
    }


def unexplained_boards(d):
    """Served counties with no board layer AND no gap record saying why.

    The project's standing rule is that every absence is recorded; this is the
    set that breaks it. Reported, never fatal — turning it into a CI failure
    would block every unrelated change until someone has researched each
    county's board-publishing posture, and a gap record invented to clear a
    build is exactly the guess the rule exists to forbid.
    """
    return sorted(
        s for s in d["served"]
        if s not in d["atlarge"]
        and "county-board" not in d["layers_by_county"].get(s, [])
        and not d["gaps_by_county"].get(s))


def render(d):
    name, fips = d["name_by_slug"], d["fips_by_slug"]

    def gap_cell(slug):
        ids = d["gaps_by_county"].get(slug, [])
        if not ids:
            return "none"
        return "%d — %s" % (len(ids), "; ".join(
            "`%s` (%s)" % (g, d["gaps"][g]["kind"]) for g in ids))

    def board_cell(slug):
        if slug in d["atlarge"]:
            return "at-large — County card"
        if "county-board" in d["layers_by_county"].get(slug, []):
            return "districted"
        # "see gaps" used to be the unconditional fallback, which pointed five
        # served counties at a record that does not exist: the judicial-circuit
        # secondaries ship a subcircuit and no board, and nothing anywhere says
        # why. An absence with no record is the one thing this project does not
        # allow itself, so the cell now NAMES the omission instead of implying a
        # record is there to read.
        if d["gaps_by_county"].get(slug):
            return "no board layer — see gaps"
        return "no board layer — **no gap record**"

    lines = [
        "# Illinois county completion status",
        "",
        "<!-- ==== GENERATED FILE — DO NOT HAND-EDIT ==== -->",
        "<!-- Emitted by scripts/build_county_status.py from the coverage-ring",
        "     lists (scripts/build_metro_outline.py), index.html's dispatch",
        "     tables, data/app/coverage-gaps.json and",
        "     data/app/il-county-commissioners.json. Regenerate:",
        "         python3 scripts/build_county_status.py",
        "     CI drift gate (smoke-test.yml):",
        "         python3 scripts/build_county_status.py --check -->",
        "",
        "**%d of 102 Illinois counties are served** — %d through their own"
        " dispatch entries, %d through a shipped judicial circuit, and %d"
        " through the County card alone. %d more are researched-but-unserved"
        " (every one carries a recorded gap saying why), leaving %d"
        " unresearched." % (
            len(d["served"]), len(d["dispatch"]), len(d["judicial"]),
            len(d["card_only"]), len(d["frontier"]), len(d["unresearched"])),
        "",
        "## How to read this",
        "",
        "- **Served through** — `dispatch`: the county has its own entries in"
        " index.html's county dispatch tables; `judicial circuit`: a secondary"
        " county of a shipped judicial circuit (its only county-specific card"
        " is the subcircuit); `County card`: an at-large county with no"
        " district geometry, its board riding the County card"
        " (`docs/EXPANSION_GUIDE.md` §3.5.1).",
        "- **Board** — how the county board surfaces: `districted` (own"
        " `county-board` dispatch entry), `at-large — County card`"
        " (data/app/il-county-commissioners.json), or `no board layer`"
        " for a served county whose board does not surface at all. That"
        " last one comes in two kinds, and the difference is the point:"
        " `see gaps` means a record says why, **`no gap record`** means"
        " nothing does — an unexplained absence, and a debt against this"
        " project's own rule that every absence is recorded.",
        "- **County-keyed dispatch entries** — read from index.html itself,"
        " the same scan `validate_index.py` check 8 gates on.",
        "- **Open gaps** — records from the guidebook's gaps block"
        " (`data/app/coverage-gaps.json`, the app's Data gaps panel). A"
        " record naming several counties appears in each of their rows.",
        "- **\"Complete\"** here means: served, and `none` in the gaps column."
        " A served county with open gaps is honest-but-unfinished; what each"
        " gap needs is the record's `wanted` line in the guidebook. One"
        " exception worth naming: a row reading **`no gap record`** in the"
        " Board column is NOT complete even though its gaps column says"
        " `none` — nobody has measured what it is missing, which is a weaker"
        " claim than having nothing missing.",
        "",
        "## Served counties (%d)" % len(d["served"]),
        "",
    ]
    unexplained = unexplained_boards(d)
    if unexplained:
        lines += [
            "> **%d served counties have no board layer and no gap record"
            " explaining it:** %s. Every one is a judicial-circuit secondary"
            " — the subcircuit is its only county-specific card — so a reader"
            " who clicks there sees no board and no note saying why."
            " Recording those gaps needs each county's actual"
            " board-publishing posture checked; a record written to clear this"
            " line would be the guess the gap system exists to prevent."
            % (len(unexplained),
               ", ".join(name[s] for s in unexplained)),
            "",
        ]
    lines += [
        "| County | FIPS | Served through | Board | County-keyed dispatch entries | Open gaps |",
        "|---|---|---|---|---|---|",
    ]
    for slug in sorted(d["served"], key=lambda s: name[s]):
        if slug in d["dispatch"]:
            tier = "dispatch"
            entries = ", ".join("`%s`" % l for l in sorted(d["layers_by_county"][slug]))
        elif slug in d["judicial"]:
            tier = "judicial circuit"
            entries = "—"
        else:
            tier = "County card"
            entries = "—"
        lines.append("| %s | %s%s | %s | %s | %s | %s |" % (
            name[slug], STATE_FIPS, fips[slug], tier, board_cell(slug),
            entries, gap_cell(slug)))

    lines += [
        "",
        "## Researched frontier (%d) — gap-recorded, not yet served" % len(d["frontier"]),
        "",
        "Counties outside the coverage ring that a research pass has already"
        " measured; each row's records say what blocks it and what a"
        " submission would need to contain.",
        "",
        "| County | FIPS | Gap records |",
        "|---|---|---|",
    ]
    for slug in sorted(d["frontier"], key=lambda s: name[s]):
        lines.append("| %s | %s%s | %s |" % (
            name[slug], STATE_FIPS, fips[slug], gap_cell(slug)))

    lines += [
        "",
        "## Unresearched (%d)" % len(d["unresearched"]),
        "",
        ", ".join(sorted(name[s] for s in d["unresearched"])) + ".",
        "",
        "## Gap records not tagged to a county (%d)" % len(d["untagged"]),
        "",
        ("None." if not d["untagged"] else
         "City- or app-scoped records with no `counties` tag, listed so the"
         " table reconciles with the %d records in the Data gaps panel: %s."
         % (len(d["gaps"]),
            ", ".join("`%s`" % g for g in d["untagged"]))),
        "",
    ]
    return "\n".join(lines)


def visible_text(html):
    """The page with its comments and scripts removed — what a reader sees.

    The phrase this gate looks for is not rare inside the app's own source. A
    build note in il/index.html describes the election-results vendor that
    serves "34 Illinois counties", which is true, unrelated, and invisible to a
    reader; scanning raw bytes flagged it as a stale coverage claim. A gate that
    cries wolf on a correct comment is a gate people learn to skip.
    """
    html = re.sub(r"(?s)<!--.*?-->", " ", html)
    html = re.sub(r"(?s)<script\b[^>]*>.*?</script>", " ", html)
    html = re.sub(r"(?s)<style\b[^>]*>.*?</style>", " ", html)
    return html


def render_stats(d):
    """The numbers, as data, at a stable public URL.

    WHY. docs/ is not published, so the only machine-readable statement of how
    many counties are served lived inside a Markdown file nobody outside this
    repo can fetch. Everyone else — overberg.co's front page and /why/ tally,
    a future press page, anyone quoting the project — retyped it by hand, and
    it went stale within a day of being corrected, twice. A number that is
    derived here and typed there will always drift; the fix is to publish it.

    NO TIMESTAMP, DELIBERATELY. Every value below is derived from repository
    state, so regenerating an unchanged repo produces an identical file and
    --check stays meaningful. A "generated" date would make this file differ on
    every run and turn the drift gate into noise.
    """
    with open(os.path.join(REPO_ROOT, "metros.json"), encoding="utf-8") as f:
        fleet = json.load(f)
    entries = fleet if isinstance(fleet, list) else fleet.get("metros", [])

    # Layer counts for the PUBLISHED fleet only, driven by metros.json rather
    # than by which worksheets exist on disk. The repo carries instances that
    # have not launched — ia/ has a full worksheet and is in no public list —
    # and globbing for worksheets would announce them in a file served at
    # districtry.com/stats.json. Illinois keeps the root worksheet; the others
    # live under their tag, the same asymmetry build_manifests.py carries.
    layers = {}
    for e in entries:
        tag = e.get("tag")
        if not tag:
            continue
        ws = "metro-worksheet.json" if tag == "il" else "%s/metro-worksheet.json" % tag
        path = os.path.join(REPO_ROOT, ws)
        if not os.path.exists(path):
            fail("metros.json publishes %r but %s does not exist" % (tag, ws))
        with open(path, encoding="utf-8") as f:
            layers[tag] = len(json.load(f).get("layers", []))

    doc = {
        "_comment": (
            "Generated by scripts/build_county_status.py from this repository's own "
            "coverage lists — do not hand-edit. Published so anything quoting these "
            "numbers can read them instead of retyping them. No timestamp: every value "
            "is derived, so an unchanged repo regenerates an identical file."),
        "source": "https://github.com/ThursdaysFamous/districtry",
        "illinois": {
            "counties_served": len(d["served"]),
            "counties_total": len(d["fips_by_slug"]),
            "counties_researched_unserved": len(d["frontier"]),
            "counties_unresearched": len(d["unresearched"]),
        },
        "gap_records": len(d["gaps"]),
        "places": len(entries),
        "layers": layers,
    }
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def check_published_counts(served):
    """Every reader-facing claim about how many Illinois counties are served
    must equal the number this script derives.

    WHY THIS EXISTS. The count lived in five places at once — metros.json's
    blurb (which the root landing page renders), README's table, and a
    cross-link on two sibling instances' SEO pages — and none of them was
    derived from anything. On 2026-08-26 all of them said 89 while this
    script, which computes the number from the coverage-ring lists, said 90.
    A generated document and a CI gate were both correct and every published
    surface was wrong, because nothing compared them.

    WHAT IT SCANS, AND WHY THAT SHAPE. metros.json's Illinois blurb by key,
    plus any HTML that says "<n> Illinois counties" or, in that blurb's own
    form, "<n> counties." HTML is the reader-facing surface by definition, so
    a page added later is covered without touching this list. Markdown, code
    comments and the schema are NOT scanned: their mentions are explanatory
    ("its coverage is 89 Illinois counties, so 'Outside Chicago' would be
    wrong"), sometimes historical, and forcing them to move with the count
    would make every county launch edit prose that was never a claim about
    today. README is scanned because its table IS a claim about today.

    Wisconsin's own "72 counties" is untouched: it never says "Illinois", and
    the bare "<n> counties." form is only read out of metros.json's il entry.

    THE FLEET TABLE'S ROWS are checked as well as its Illinois count, and the
    reason is Iowa. This gate read the Illinois row's number and nothing else,
    so when Iowa shipped as the fifth instance README went on saying "four
    instances" with no Iowa row at all, and every check in the repo stayed
    green — the number it watched had not moved. A count that is right about
    the row it reads says nothing about a row that is missing. So metros.json
    is the roster: every instance must have a table row naming its landing name
    and its URL, and the prose count of instances must equal how many there
    are. The row's "Covers" prose stays hand-written; only its existence and
    its identity are derived.

    funding.json is scanned too, and it is the reason this docstring gained a
    fourth surface. It is a FLOSS/fund manifest served at
    districtry.com/funding.json — reader-facing by construction, since a funder
    reads it — but it is JSON, so the HTML sweep below cannot see it, and its
    project description states the served count outright. A number published to
    a funding directory is exactly the kind that must not drift.
    """
    bad = []

    # 1. the fleet manifest's Illinois blurb — what the landing page renders
    with open(os.path.join(REPO_ROOT, "metros.json"), encoding="utf-8") as f:
        fleet = json.load(f)
    entries = fleet if isinstance(fleet, list) else fleet.get("metros", [])
    for e in entries:
        if e.get("tag") != "il":
            continue
        m = re.match(r"\s*(\d+)\s+counties\b", e.get("blurb", ""))
        if not m:
            bad.append("metros.json: the il blurb no longer opens with "
                       "'<n> counties' — this gate reads it there")
        elif int(m.group(1)) != served:
            bad.append("metros.json: il blurb says %s counties, derived is %d"
                       % (m.group(1), served))

    # 2. every reader-facing page, plus README's table
    # README's fleet table states the count without the word "Illinois", so the
    # phrase scan below cannot see it. It is a claim about today, so it is read
    # by its own row rather than left uncovered — the first draft of this gate
    # claimed to scan README and did not.
    readme = os.path.join(REPO_ROOT, "README.md")
    with open(readme, encoding="utf-8") as f:
        for line in f:
            if not line.lstrip().startswith("| **Illinois**"):
                continue
            m = re.search(r"\|\s*(\d+)\s+counties\b", line)
            if not m:
                bad.append("README.md: the Illinois row no longer states "
                           "'<n> counties' — this gate reads it there")
            elif int(m.group(1)) != served:
                bad.append("README.md: Illinois row says %s counties, derived is %d"
                           % (m.group(1), served))
            break

    for e in NOT_THE_SERVED_COUNT:
        if not os.path.isfile(os.path.join(REPO_ROOT, e["page"])):
            bad.append("NOT_THE_SERVED_COUNT excuses %s (%s) and that page is "
                       "gone — drop the entry" % (e["page"], e["date"]))

    targets = sorted(glob.glob(os.path.join(REPO_ROOT, "*.html")) +
                     glob.glob(os.path.join(REPO_ROOT, "*", "*.html")))
    for path in targets:
        rel = os.path.relpath(path, REPO_ROOT)
        # The noindexed rebrand preview under districtry/ is excluded. Matched
        # on the RELATIVE path's first component: the repo directory is itself
        # named districtry, so testing the absolute path for os.sep+districtry
        # +os.sep silently skipped every file in the repo — the first draft of
        # this gate did exactly that and passed a deliberately broken page.
        if rel.split(os.sep)[0] == "districtry":
            continue
        # engine/index.html is a DIRECTORY — the per-fence store compose_app.py
        # splices from — not a page. The glob cannot tell.
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as f:
            text = visible_text(f.read())
        excused = next((e for e in NOT_THE_SERVED_COUNT
                        if e["page"] == rel.replace(os.sep, "/")), None)
        found = list(re.finditer(r"(\d+)\s+Illinois\s+counties", text))
        if excused:
            if not found:
                bad.append("%s is excused from this sweep (%s) and no longer "
                           "carries an '<n> Illinois counties' claim — drop the "
                           "NOT_THE_SERVED_COUNT entry" % (rel, excused["date"]))
            else:
                print("build-county-status: ~ %s says %s Illinois counties and "
                      "is not the served count (%s): %s"
                      % (rel, found[0].group(1), excused["date"],
                         excused["reason"]))
            continue
        for m in found:
            if int(m.group(1)) != served:
                bad.append("%s: says %s Illinois counties, derived is %d"
                           % (rel, m.group(1), served))

    # 3. README's fleet table — a row per instance, and the prose count.
    # Read from metros.json, which is the fleet's own manifest: the landing
    # page, the coverage map and the privacy page are all generated from it, so
    # an instance that is live is in it by construction.
    with open(readme, encoding="utf-8") as f:
        readme_text = f.read()
    words = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
             6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten"}
    for e in entries:
        name, url = e.get("landing_name", ""), e.get("url", "")
        row = [ln for ln in readme_text.splitlines()
               if ln.startswith("| **%s**" % name)]
        if not row:
            bad.append("README.md: no fleet-table row for %s, which metros.json "
                       "lists as live at %s" % (name, url))
        elif url and url not in row[0]:
            bad.append("README.md: the %s row does not link %s" % (name, url))
    want = words.get(len(entries), str(len(entries)))
    for m in re.finditer(r"\b(one|two|three|four|five|six|seven|eight|nine|ten)\s+instances\b",
                         readme_text):
        if m.group(1) != want:
            bad.append("README.md: says '%s instances', metros.json lists %d"
                       % (m.group(1), len(entries)))

    # 4. the FLOSS/fund manifest. Every string value is swept rather than one
    # named field: the count sits in the project description today, and a
    # reworded manifest that moves it into a plan's description would silently
    # leave this gate reading a field that no longer carries the claim.
    funding = os.path.join(REPO_ROOT, "funding.json")
    if os.path.exists(funding):
        with open(funding, encoding="utf-8") as f:
            manifest = json.load(f)

        def strings(node):
            if isinstance(node, str):
                yield node
            elif isinstance(node, dict):
                for v in node.values():
                    for out in strings(v):
                        yield out
            elif isinstance(node, list):
                for v in node:
                    for out in strings(v):
                        yield out

        seen = False
        for value in strings(manifest):
            for m in re.finditer(r"(\d+)\s+Illinois\s+counties", value):
                seen = True
                if int(m.group(1)) != served:
                    bad.append("funding.json: says %s Illinois counties, "
                               "derived is %d" % (m.group(1), served))
        if not seen:
            bad.append("funding.json: no '<n> Illinois counties' claim found — "
                       "this gate reads the served count there, so a reword "
                       "that drops the phrase leaves the manifest unguarded")
    return bad


# "<n> Illinois counties" that is NOT the served-county claim.
#
# The page sweep below reads every "<n> Illinois counties" as a statement of how
# far this site's county-dispatched layers reach, which held while that was the
# only reason to write the phrase. il/judicial-subcircuit.html writes it about a
# different set entirely — the counties whose circuit judges are elected from a
# subcircuit — and there is nothing in the sentence a regex can tell apart.
#
# So the exception is stated, in the shape ACCEPTED_DROPS and
# EXPECTED_UNREACHABLE already use: a reason, a date, and a re-audit every run.
# An entry whose file is gone FAILS, and so does one whose file no longer
# carries the phrase it excuses — which is what stops it outliving its subject.
# The excused number is not unguarded: build_concept_pages.py derives it from
# il/index.html's own dispatch entries on the run that writes the page, so it
# cannot be hand-typed, which is the failure this sweep exists to catch.
NOT_THE_SERVED_COUNT = [
    dict(page="il/judicial-subcircuit.html",
         reason="the counties that elect circuit judges from a subcircuit, "
                "derived by build_concept_pages.py from il/index.html's own "
                "judicial-subcircuit dispatch entries",
         date="2026-09-16"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="verify the shipped file, write nothing")
    args = ap.parse_args()

    d = derive(*load_inputs())
    payload = render(d)
    # Counted here rather than left to a reader scanning 59 table rows: a served
    # county whose board is absent AND unexplained is a debt, and a number in
    # every run's output is how it stays visible until it reaches zero.
    unexplained = unexplained_boards(d)
    summary = ("%d served (%d dispatch, %d judicial, %d card), %d frontier, "
               "%d unresearched, %d gap records" % (
                   len(d["served"]), len(d["dispatch"]), len(d["judicial"]),
                   len(d["card_only"]), len(d["frontier"]),
                   len(d["unresearched"]), len(d["gaps"])))
    if unexplained:
        summary += ("; %d served with NO board layer and NO gap record (%s)"
                    % (len(unexplained),
                       ", ".join(d["name_by_slug"][s] for s in unexplained)))

    if args.check:
        if not os.path.exists(OUT_PATH):
            fail("docs/COUNTY_STATUS.md is missing — run this script")
        with open(OUT_PATH, encoding="utf-8") as f:
            shipped = f.read()
        if shipped != payload:
            fail("docs/COUNTY_STATUS.md is stale (%d vs %d bytes). It is "
                 "generated, never hand-edited — rerun "
                 "python3 scripts/build_county_status.py"
                 % (len(shipped), len(payload)))
        want_stats = render_stats(d)
        have_stats = (open(STATS_PATH, encoding="utf-8").read()
                      if os.path.exists(STATS_PATH) else "")
        if have_stats != want_stats:
            fail("stats.json is stale or missing — it is generated, never "
                 "hand-edited. Rerun python3 scripts/build_county_status.py")
        stale = check_published_counts(len(d["served"]))
        if stale:
            fail("%d published count(s) disagree with the derived %d:\n  - %s"
                 % (len(stale), len(d["served"]), "\n  - ".join(stale)))
        print("build-county-status: OK — %s; published counts agree; stats.json current" % summary)
        return

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(payload)
    with open(STATS_PATH, "w", encoding="utf-8") as f:
        f.write(render_stats(d))
    print("build-county-status: wrote %s — %s"
          % (os.path.relpath(OUT_PATH, REPO_ROOT), summary))


if __name__ == "__main__":
    main()
