#!/usr/bin/env python3
"""
Weekly fleet-status aggregator (docs/MECHANIZATION_PLAYBOOK.md, Conversion 3).

Runs in this repo only (one report, one checkout). Originally compared CHI
against separate per-metro fork repos; those forks are retired as of R5 —
every metro is now a folder in this same repo — so two of the original checks
(the engine.lock.json pin, and diffing each fork's own docs/ENGINE_SYNC.md
against CHI's) no longer have anything to compare against and were removed
rather than left to report a trivial "in sync" against themselves. What
remains, read straight off this checkout for every instance in metros.json:

  - validator capabilities: the CAPABILITIES list parsed from the instance's
    own scripts/validate_index.py, diffed against CHI's. A capability present
    in an instance but absent in CHI is a **reverse-parity WARN** — the
    back-port debt this workflow exists to surface;
  - scraper health: last completed run per workflow named in the instance's
    metro-worksheet.json, plus any per-field coverage one-liners greppable
    from that run's log. Also flags a workflow file that is not actually in
    the repo ROOT .github/workflows/ (GitHub Actions only reads there) as
    **INERT** — an instance folder brings its own .github/ along, and every
    file in it looks like a live refresh while never running;
  - workflow name collisions: two instances inventorying the same workflow
    BASENAME, which can only be one file at the shared root — so at most one
    of them is telling the truth about that refresh. Reported loudly rather
    than letting the health check above answer confidently about the wrong
    file, which is how six of the ten workflows once found INERT were missed
    on the first pass;
  - guidebook coverage: the instance's worksheet layer roster diffed against
    the coverage map in docs/DATA_LAYER_GUIDEBOOK.md. A layer shipped without
    a guidebook row (or a guidebook row no instance backs) is a **GUIDEBOOK
    WARN**;
  - data-gaps drift: the instance's shipped data/app/coverage-gaps.json
    compared to what the guidebook's gaps block would emit for that metro. A
    mismatch is a **GAPS WARN**. Since 2026-09-02 this is also gated directly
    in CI (smoke-test.yml runs build_coverage_gaps.py --check for all five
    metros), so this is now a second, weekly-cadence check on the same
    invariant rather than the only one;
  - CHI's own ENGINE_SYNC.md inventory checked against the real ENGINE fences
    in il/index.html and il/sw.js — the doc that opens "the SAME copy ships in
    every fork; never edit it in one fork only" had drifted 164 lines with an
    inventory naming 50 blocks when the fences held 53, because
    check_engine_parity.py compares fenced CODE and nothing compared the
    document (ENGINE_SYNC backlog item 14). CHI-only now for the same reason
    the cross-fork diff above was removed: one copy of the doc, one repo,
    nothing left to diff it against;
  - open bot PRs (roster + engine-bump branches awaiting human review).

Emits a markdown report and a status word (ok|warn). It never edits anything —
the workflow posts the report to a single auto-updated tracking issue and the
job stays green; the issue is the signal (the validate-sources convention).

Stdlib only. Network: api.github.com (+ raw file contents via the API), using
the GH_TOKEN env var when present.

Usage:
    python3 scripts/fleet_status.py [--manifest metros.json]
        [--report fleet-status.md] [--status-file status.txt]
"""

import argparse
import io
import json
import os
import re
import sys
import urllib.error
import urllib.request
import zipfile

API = "https://api.github.com"
CAP_RE = re.compile(r"^CAPABILITIES\s*=\s*\[(.*?)\]", re.DOTALL | re.MULTILINE)
GUIDEBOOK_PATH = os.path.join("docs", "DATA_LAYER_GUIDEBOOK.md")
GUIDEBOOK_RE = re.compile(
    r"<!-- ==== GUIDEBOOK:BEGIN coverage-map ==== -->\s*```json\s*(.*?)\s*```",
    re.DOTALL)
GAPS_RE = re.compile(
    r"<!-- ==== GUIDEBOOK:BEGIN gaps ==== -->\s*```json\s*(.*?)\s*```",
    re.DOTALL)
GAPS_PATH = "data/app/coverage-gaps.json"

# WHERE EACH INSTANCE LIVES. This used to be a remote-fetch problem: three
# separate fork repos, each read over the GitHub contents API. The
# consolidation ended that — il/ at R2.3, ny/ and ca/ imported at R3 and
# published at R5 — so every file this script wants is on disk beside it, and
# reading them over the network was checking repos that are no longer deployed.
# The path table is IMPORTED from the generator rather than restated here: two
# copies of "where does ny/ keep its worksheet" is precisely the drift class
# this file exists to catch.
try:
    from generate_metro_files import INSTANCES  # noqa: E402
except ImportError:  # pragma: no cover — reported as a WARN by the caller
    INSTANCES = None


def local_path(repo_root, tag, kind, rel=""):
    """Absolute path of an instance-owned file. `kind` keys INSTANCES."""
    base = INSTANCES[tag][kind]
    parts = [repo_root] + ([] if base == "." else [base]) + ([rel] if rel else [])
    return os.path.join(*parts)


def read_local(path):
    """File contents, or None — the local counterpart of the old fetch_file."""
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None
ENGINE_SYNC_PATH = os.path.join("docs", "ENGINE_SYNC.md")
# "## Current ENGINE block inventory (53 in index.html + 2 in sw.js)" followed
# by the backticked block list on the "index.html: ..." line(s).
INVENTORY_COUNTS_RE = re.compile(
    r"## Current ENGINE block inventory \((\d+) in index\.html \+ (\d+) in sw\.js\)")
# The two labelled lists, each running from its "<file>: " label to the first
# period that ends it. Anchored per list rather than over the whole section:
# the prose after the lists is full of backticked block names in passing
# ("it sits between the `feedback` fence and the geocoder"), and a section-wide
# scrape reads those as inventory entries.
# Each list runs from its "<file>: " label to the first thing that ends it — a
# period at end of line, or an em-dash beginning the trailing commentary the
# sw.js entry carries ("`sw-header`, `sw-handlers` — the config between them…").
# Anchored per list rather than scraped section-wide: the prose after the lists
# is full of backticked block names in passing ("it sits between the `feedback`
# fence and the geocoder"), and a section-wide scrape reads those as entries —
# which is exactly what the first draft of this check did, warning on a
# perfectly in-sync repo.
INVENTORY_LIST_RE = {
    "index.html": re.compile(r"^index\.html: (.*?)(?:\.$| —)", re.DOTALL | re.MULTILINE),
    "sw.js": re.compile(r"^sw\.js: (.*?)(?:\.$| —)", re.DOTALL | re.MULTILINE),
}

# The expected payload is produced by the BUILDER's own render(), imported rather
# than reimplemented: a second copy of that serialization would be exactly the
# kind of drift this check exists to catch.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from build_coverage_gaps import render as render_gaps  # noqa: E402
except ImportError:  # pragma: no cover — reported as a WARN by the caller
    render_gaps = None

# Same rule for the fence parser: the inventory check must read fences with the
# SAME parser the parity gate uses, or the two could disagree about what a block
# even is — which is the class of drift this whole file exists to catch.
try:
    from check_engine_parity import extract_blocks  # noqa: E402
except ImportError:  # pragma: no cover — reported as a WARN by the caller
    extract_blocks = None


def api_get(path, raw=False):
    req = urllib.request.Request(API + path, headers={
        "User-Agent": "districtry-fleet-status",
        "Accept": "application/vnd.github.raw+json" if raw else "application/vnd.github+json",
    })
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    return data if raw else json.loads(data.decode("utf-8"))


def parse_capabilities(validator_text):
    m = CAP_RE.search(validator_text or "")
    if not m:
        return None  # instance hasn't declared yet — reported as such, not a WARN
    return sorted(re.findall(r'"([a-z0-9-]+)"', m.group(1)))


def load_guidebook_map(repo_root):
    """The per-metro layer-id lists from the guidebook's coverage-map block,
    or None if the guidebook / block is missing or unparseable (reported as a
    WARN by the caller — a broken guidebook must not pass silently)."""
    try:
        with open(os.path.join(repo_root, GUIDEBOOK_PATH), encoding="utf-8") as f:
            m = GUIDEBOOK_RE.search(f.read())
        return json.loads(m.group(1)) if m else None
    except (OSError, ValueError):
        return None


def guidebook_diff(gb_map, metro_id, layer_ids):
    """(report_line, warn_list) for one metro's roster vs the guidebook map."""
    listed = gb_map.get(metro_id)
    if listed is None:
        w = "%s: metro missing from the guidebook coverage map" % metro_id
        return ("- Guidebook coverage: **GUIDEBOOK WARN — metro not in the coverage map**", [w])
    unlisted = sorted(set(layer_ids) - set(listed))
    phantom = sorted(set(listed) - set(layer_ids))
    warns = []
    if unlisted:
        warns.append("%s: GUIDEBOOK — shipped layers not in the guidebook: %s"
                     % (metro_id, ", ".join(unlisted)))
    if phantom:
        warns.append("%s: GUIDEBOOK — guidebook lists layers the instance doesn't register: %s"
                     % (metro_id, ", ".join(phantom)))
    if warns:
        line = ("- Guidebook coverage: **GUIDEBOOK WARN** — "
                + ("unlisted: %s" % ", ".join("`%s`" % i for i in unlisted) if unlisted else "")
                + ("; " if unlisted and phantom else "")
                + ("phantom: %s" % ", ".join("`%s`" % i for i in phantom) if phantom else "")
                + ". Update docs/DATA_LAYER_GUIDEBOOK.md in the change that touched the roster.")
    else:
        line = "- Guidebook coverage: in sync (%d layers)" % len(layer_ids)
    return (line, warns)


def load_guidebook_gaps(repo_root):
    """The per-metro gap arrays from the guidebook's gaps block, or None if the
    guidebook / block is missing or unparseable."""
    try:
        with open(os.path.join(repo_root, GUIDEBOOK_PATH), encoding="utf-8") as f:
            m = GAPS_RE.search(f.read())
        return json.loads(m.group(1)) if m else None
    except (OSError, ValueError):
        return None


def gaps_diff(gaps_map, metro_id, shipped_text):
    """(report_line, warn_list) for one instance's shipped gaps file vs the guidebook.

    Four states, and only two of them are warnings:
      - guidebook has no array AND the instance ships nothing  -> consistent, silent
      - guidebook has an array, instance's file matches it      -> in sync
      - the two disagree, either way round                  -> GAPS WARN
    """
    listed = gaps_map.get(metro_id)
    shipped = shipped_text is not None

    if listed is None and not shipped:
        return ("- Data gaps: none recorded (no guidebook array, no shipped file)", [])
    if listed is None:
        w = ("%s: GAPS — ships %s but the guidebook records no gaps array for this "
             "metro" % (metro_id, GAPS_PATH))
        return ("- Data gaps: **GAPS WARN** — file shipped with no guidebook array", [w])
    if not shipped:
        w = ("%s: GAPS — guidebook records %d gap(s) but the instance ships no %s"
             % (metro_id, len(listed), GAPS_PATH))
        return ("- Data gaps: **GAPS WARN** — %d recorded, none shipped" % len(listed), [w])
    if render_gaps is None:
        return ("- Data gaps: builder import failed — drift unchecked",
                ["%s: GAPS — could not import build_coverage_gaps.render" % metro_id])

    try:
        expected = render_gaps(listed)
    except (KeyError, TypeError) as e:
        return ("- Data gaps: **GAPS WARN** — guidebook array is malformed",
                ["%s: GAPS — guidebook gaps array will not render: %s" % (metro_id, e)])

    if shipped_text.strip() == expected.strip():
        return ("- Data gaps: in sync (%d gap%s)"
                % (len(listed), "" if len(listed) == 1 else "s"), [])

    # Name WHICH ids differ — "the bytes differ" is not actionable at 7am.
    try:
        have = set(json.loads(shipped_text))
    except ValueError:
        have = None
    want = {e["id"] for e in listed if isinstance(e, dict) and e.get("id")}
    if have is None:
        detail = "shipped file is not valid JSON"
    else:
        only_shipped = sorted(have - want)
        only_guide = sorted(want - have)
        bits = []
        if only_guide:
            bits.append("missing from the instance: %s" % ", ".join(only_guide))
        if only_shipped:
            bits.append("shipped but not recorded: %s" % ", ".join(only_shipped))
        # same ids on both sides means a FIELD changed — the common case after
        # someone edits a summary, why or wanted line and forgets to regenerate
        # (a `blocker` edit changes nothing here: it is the maintainer's record
        # and build_coverage_gaps.py does not emit it)
        detail = "; ".join(bits) or "same %d ids, but content differs" % len(want)
    w = "%s: GAPS — shipped %s is out of date (%s). Regenerate with %s" % (
        metro_id, GAPS_PATH, detail,
        "scripts/build_coverage_gaps.py" if metro_id == "chicago"
        else "scripts/build_coverage_gaps.py --metro %s --out <tag>/%s" % (metro_id, GAPS_PATH))
    return ("- Data gaps: **GAPS WARN** — %s" % detail, [w])


def parse_inventory(doc_text):
    """(counts, {file: [block names]}) from the doc's inventory section, or None
    if the heading or either labelled list is missing."""
    m = INVENTORY_COUNTS_RE.search(doc_text or "")
    if not m:
        return None
    listed = {}
    for fname, rx in INVENTORY_LIST_RE.items():
        lm = rx.search(doc_text)
        if not lm:
            return None
        listed[fname] = re.findall(r"`([a-z0-9][a-z0-9-]*)`", lm.group(1))
    return ((int(m.group(1)), int(m.group(2))), listed)


def inventory_diff(repo_root):
    """(report_line, warn_list) for CHI's ENGINE_SYNC inventory vs its real fences.

    CHI-only on purpose: since R5 there is one copy of docs/ENGINE_SYNC.md and
    one copy of the ENGINE fences, both in this repo — re-reading them once
    per instance would add network for no new signal, since every instance
    would report the identical answer. (Before the fork consolidation this
    check also diffed each fork's own copy of the doc against CHI's; that half
    is gone along with the forks it compared, per the module docstring.)
    Checking the canonical copy against the canonical fences is what catches
    the real failure: a release that adds blocks and never updates the list,
    which is how the count sat at 50 while the fences held 53.
    """
    try:
        with open(os.path.join(repo_root, ENGINE_SYNC_PATH), encoding="utf-8") as f:
            doc = f.read()
    except OSError:
        return ("- ENGINE_SYNC inventory: **SYNC WARN** — %s unreadable" % ENGINE_SYNC_PATH,
                ["engine-sync: %s is unreadable in CHI" % ENGINE_SYNC_PATH])
    if extract_blocks is None:
        return ("- ENGINE_SYNC inventory: parser import failed — unchecked",
                ["engine-sync: could not import check_engine_parity.extract_blocks"])

    parsed = parse_inventory(doc)
    if parsed is None:
        return ("- ENGINE_SYNC inventory: **SYNC WARN** — inventory section missing or unparseable",
                ["engine-sync: the ENGINE block inventory section in %s could not be parsed"
                 % ENGINE_SYNC_PATH])
    (said_idx, said_sw), listed = parsed

    actual = {}
    for fname in ("index.html", "sw.js"):
        try:
            with open(os.path.join(repo_root, "il", fname), encoding="utf-8") as f:
                actual[fname] = sorted(extract_blocks(f.read(), fname))
        except (OSError, ValueError) as e:
            return ("- ENGINE_SYNC inventory: **SYNC WARN** — cannot read fences from %s" % fname,
                    ["engine-sync: cannot read ENGINE fences from %s (%s)" % (fname, e)])
    idx, sw = actual["index.html"], actual["sw.js"]

    missing, phantom = [], []
    for fname, fenced in (("index.html", idx), ("sw.js", sw)):
        have = listed[fname]
        missing += ["%s (%s)" % (b, fname) for b in fenced if b not in have]
        phantom += ["%s (%s)" % (b, fname) for b in have if b not in fenced]
    counts_ok = (said_idx == len(idx) and said_sw == len(sw))
    if counts_ok and not missing and not phantom:
        return ("- ENGINE_SYNC inventory: in sync (%d in index.html + %d in sw.js)"
                % (len(idx), len(sw)), [])

    bits = []
    if not counts_ok:
        bits.append("heading says %d+%d, fences hold %d+%d" % (said_idx, said_sw, len(idx), len(sw)))
    if missing:
        bits.append("fenced but not listed: %s" % ", ".join(missing))
    if phantom:
        bits.append("listed but not fenced: %s" % ", ".join(phantom))
    detail = "; ".join(bits)
    return ("- ENGINE_SYNC inventory: **SYNC WARN** — %s" % detail,
            ["engine-sync: %s's block inventory is stale (%s). Regenerate it from the "
             "fences rather than editing the list by hand — hand-maintenance is how it "
             "went stale before." % (ENGINE_SYNC_PATH, detail)])


def workflow_health(repo, wf_file):
    """(conclusion, date, coverage_lines) of the last completed run."""
    try:
        runs = api_get("/repos/%s/actions/workflows/%s/runs?per_page=1&status=completed" % (repo, wf_file))
        run = runs["workflow_runs"][0]
    except (urllib.error.URLError, LookupError):
        return ("no runs", "", [])
    coverage = []
    try:
        blob = api_get("/repos/%s/actions/runs/%d/logs" % (repo, run["id"]), raw=True)
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            for name in z.namelist():
                for line in z.read(name).decode("utf-8", "replace").splitlines():
                    if re.search(r"coverage", line, re.IGNORECASE):
                        coverage.append(re.sub(r"^\S+\s", "", line).strip())
    except Exception:  # noqa: BLE001 — coverage is best-effort garnish, never a failure
        pass
    return (run.get("conclusion") or "?", (run.get("run_started_at") or "")[:10], coverage[:4])


def open_bot_prs(repo):
    try:
        prs = api_get("/repos/%s/pulls?state=open&per_page=100" % repo)
        return sorted("#%d (%s)" % (p["number"], p["head"]["ref"]) for p in prs
                      if p["head"]["ref"].startswith("bot/"))
    except urllib.error.URLError:
        return []


def workflow_name_collisions(repo_root):
    """Instances that inventory the same workflow BASENAME.

    WHY THIS IS SEPARATE FROM THE INERT CHECK BELOW. That check asks whether a
    worksheet's workflow exists in the root .github/workflows — and a name is
    all it can ask, because a workflow file carries nothing that says which
    instance it serves. So when two instances inventory the same basename, the
    check answers about whichever single file the root actually holds, and
    reports the other instance's frozen refresh as healthy. That is exactly what
    happened: `update-congress-roster.yml` and `validate-sources.yml` were in
    all three worksheets, Chicago's copies sat at the root, and NYC's and SF's
    four refreshes read as present while nothing ran them. Six inert workflows
    were found; ten were inert.

    A shared basename is therefore a FAILURE OF THE INVENTORY, not a detail:
    at the root only one file can hold a name, so at most one of the instances
    claiming it can be right. Say so loudly rather than letting the check below
    answer confidently about the wrong file.
    """
    if INSTANCES is None:
        return []
    owners = {}
    for tag, inst in INSTANCES.items():
        raw = read_local(os.path.join(repo_root, inst["worksheet"]))
        if not raw:
            continue
        try:
            ws = json.loads(raw)
        except ValueError:
            continue
        for wf in ws.get("workflows", []):
            owners.setdefault(wf.get("file"), []).append(tag)
    return [(name, tags) for name, tags in sorted(owners.items()) if len(tags) > 1]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", default="metros.json")
    ap.add_argument("--report", help="write the markdown report here (default: stdout)")
    ap.add_argument("--status-file", help="write ok|warn here")
    args = ap.parse_args()

    with open(args.manifest, encoding="utf-8") as f:
        manifest = json.load(f)
    metros = manifest["metros"]
    chi = next(m for m in metros if m["id"] == "chicago")

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "validate_index.py"),
              encoding="utf-8") as f:
        chi_caps = parse_capabilities(f.read()) or []

    warns = []
    lines = ["# Fleet status", ""]
    lines.append("All %d instance(s) live in `%s` and are read from this checkout; "
                 "only workflow runs and open PRs still need the API."
                 % (len(metros), chi["repo"]))
    lines.append("")

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    gb_map = load_guidebook_map(repo_root)
    if gb_map is None:
        warns.append("guidebook: %s missing or its coverage-map block is unparseable" % GUIDEBOOK_PATH)
        lines.append("**GUIDEBOOK WARN:** `%s` missing or unparseable — layer-parity checks skipped." % GUIDEBOOK_PATH)
        lines.append("")
    gaps_map = load_guidebook_gaps(repo_root)
    if gaps_map is None:
        warns.append("guidebook: gaps block missing or unparseable — data-gaps drift unchecked")
        lines.append("**GAPS WARN:** the guidebook's gaps block is missing or unparseable — "
                     "data-gaps drift unchecked in every instance.")
        lines.append("")

    inv_line, inv_warns = inventory_diff(repo_root)
    lines.append(inv_line)
    lines.append("")
    warns.extend(inv_warns)

    bot_prs = open_bot_prs(chi["repo"])
    if bot_prs:
        lines.append("- Open bot PRs (roster + engine-bump branches awaiting human review): %d" % len(bot_prs))
        for pr in bot_prs:
            lines.append("  - %s" % pr)
    else:
        lines.append("- Open bot PRs: none")
    lines.append("")

    collisions = workflow_name_collisions(repo_root)
    if collisions:
        lines.append("**WORKFLOW NAME COLLISION:** the root `.github/workflows/` "
                     "holds one file per name, so an inventory two instances "
                     "share cannot be checked for either of them.")
        for name, tags in collisions:
            warns.append("workflows: `%s` is inventoried by %s — at the root only "
                         "one file can hold that name, so the inert check below "
                         "answers about whichever instance owns it and reports the "
                         "others as healthy. Give each a distinct prefixed name."
                         % (name, " and ".join(sorted(tags))))
            lines.append("  - ⛔ `%s` — claimed by %s" % (name, ", ".join(sorted(tags))))
        lines.append("")

    for m in metros:
        repo = m["repo"]
        tag = m.get("tag")
        if not tag or INSTANCES is None or tag not in INSTANCES:
            warns.append("%s: no instance folder for tag %r — cannot check it locally"
                         % (m["id"], tag))
            lines.append("## %s" % m["label"])
            lines.append("")
            lines.append("- **INSTANCE WARN** — metros.json gives tag %r, which is not an "
                         "instance in generate_metro_files.INSTANCES. Every check below "
                         "needs that folder, so all of them are skipped." % tag)
            lines.append("")
            continue
        lines.append("## %s (`%s/`)" % (m["label"], tag))
        lines.append("")

        # The engine-pin check is GONE, not broken. R2.1 retired the release
        # channel and deleted engine.lock.json: one repo, one copy of the
        # engine, and compose_app.py --check proves every instance carries it.
        # Reporting "Engine pin: not found" three times a week was noise about
        # a mechanism that no longer exists.
        caps = parse_capabilities(read_local(
            local_path(repo_root, tag, "scripts", "validate_index.py")))
        if caps is None:
            lines.append("- Validator capabilities: not declared yet (Conversion 3 §3.1)")
        elif m["id"] == "chicago":
            lines.append("- Validator capabilities: %d declared (the reference set)" % len(caps))
        else:
            ahead = sorted(set(caps) - set(chi_caps))
            behind = sorted(set(chi_caps) - set(caps))
            if ahead:
                warns.append("%s: REVERSE-PARITY — capabilities not in CHI: %s" % (m["id"], ", ".join(ahead)))
                lines.append("- Validator capabilities: **REVERSE-PARITY WARN — instance has %s; CHI lacks them.** "
                             "Back-port to CHI within one release cycle (docs/ENGINE_SYNC.md DoD)." % ", ".join("`%s`" % c for c in ahead))
            else:
                lines.append("- Validator capabilities: no reverse-parity debt")
            if behind:
                lines.append("  (instance missing vs CHI: %s — forward parity, arrives via normal porting)" % ", ".join("`%s`" % c for c in behind))

        ws_raw = read_local(os.path.join(repo_root, INSTANCES[tag]["worksheet"]))
        ws = None
        if ws_raw:
            try:
                ws = json.loads(ws_raw)
            except ValueError:
                pass
        wfs = (ws or {}).get("workflows", [])

        if gb_map is not None:
            if ws is None:
                warns.append("%s: worksheet unreadable — guidebook coverage unchecked" % m["id"])
                lines.append("- Guidebook coverage: **worksheet unreadable — unchecked**")
            else:
                gb_line, gb_warns = guidebook_diff(
                    gb_map, m["id"], [l.get("id") for l in ws.get("layers", [])])
                lines.append(gb_line)
                warns.extend(gb_warns)

        # Data-gaps drift. Deliberately NOT nested under the worksheet check
        # above: the gaps file is compared to the guidebook directly and does not
        # need the instance's worksheet, so an unreadable worksheet must not silently
        # take this check down with it.
        if gaps_map is not None:
            gaps_line, gaps_warns = gaps_diff(
                gaps_map, m["id"], read_local(local_path(repo_root, tag, "app", GAPS_PATH)))
            lines.append(gaps_line)
            warns.extend(gaps_warns)

        if not wfs:
            lines.append("- Scrapers: worksheet not found — no workflow inventory (Conversion 2 pending?)")
        else:
            lines.append("- Scrapers (last completed run):")
            for wf in wfs:
                # GITHUB ACTIONS ONLY READS THE REPOSITORY ROOT'S .github/workflows.
                # An instance imported as a folder brings its .github/ with it, and
                # every file in there is INERT — it looks like a live refresh and
                # never runs. Nothing caught that before, because this script asked
                # the old fork repo, where the same file genuinely does run. Ask the
                # checkout where the file actually is, and say so.
                if not os.path.isfile(os.path.join(repo_root, ".github", "workflows", wf["file"])):
                    stray = os.path.join(repo_root, tag, ".github", "workflows", wf["file"])
                    where = ("`%s/.github/workflows/` — NOT run by Actions" % tag
                             if os.path.isfile(stray) else "absent from the checkout")
                    warns.append("%s: %s is not in the root .github/workflows (%s) — "
                                 "it cannot run, so whatever it refreshes is frozen"
                                 % (m["id"], wf["file"], where))
                    lines.append("  - ⛔ `%s` **INERT — %s**" % (wf["file"], where))
                    continue
                concl, date, cov = workflow_health(repo, wf["file"])
                if concl not in ("success", "no runs"):
                    warns.append("%s: %s last run %s (%s)" % (m["id"], wf["file"], concl, date))
                mark = "✅" if concl == "success" else ("➖" if concl == "no runs" else "❌")
                lines.append("  - %s `%s` %s %s" % (mark, wf["file"], concl, date))
                for c in cov:
                    lines.append("    - coverage: `%s`" % c)

        # The cross-fork ENGINE_SYNC diff is GONE for the same reason as the
        # engine pin: it compared each fork's copy of the doc against CHI's, and
        # there is now ONE copy in ONE repo. It was warning that "the fork
        # carries no docs/ENGINE_SYNC.md" about folders that were never supposed
        # to have their own. The inventory check above still validates that doc
        # against the real fences, which is the part that was ever load-bearing.
        lines.append("")

    status = "warn" if warns else "ok"
    lines.append("---")
    if warns:
        lines.append("**%d WARN(s):**" % len(warns))
        for w in warns:
            lines.append("- %s" % w)
    else:
        lines.append("No WARNs — fleet is current.")
    report = "\n".join(lines) + "\n"

    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            f.write(report)
    else:
        print(report)
    if args.status_file:
        with open(args.status_file, "w") as f:
            f.write(status)
    print("fleet-status: %s — %d warn(s)" % (status.upper(), len(warns)), file=sys.stderr)


if __name__ == "__main__":
    main()
