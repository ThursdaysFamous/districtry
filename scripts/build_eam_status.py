#!/usr/bin/env python3
"""
Emit docs/EAM_STATUS.md — whether each state instance is EXAMINED, ANSWERED
and MAINTAINED, computed from the tree on every run.

WHY THIS EXISTS. "When is a state done?" had no answer, so nothing could be
declared finished and no session could be moved off expansion. The obvious
definition — no gaps left — is worse than useless here and inverts the
incentive: Illinois carries 104 gap records and is the DEEPEST instance in the
fleet, while an instance with two records is more likely under-researched than
complete. A gap record is how an absence is made visible; counting them
punishes looking.

So E.A.M. measures three things the project controls, rather than one thing
county publishers control (ruled by Adam, 2026-09-22):

  EXAMINED    Every county in the state is either served by a roster or named
              by a gap record. Not "we shipped everywhere" — "we looked
              everywhere, and where we could not ship, a record says why."
              The denominator is the whole state, never the coverage ring.

  ANSWERED    Every district these pages draw either names a member, is marked
              vacant by the county, or carries a note saying why no name can
              be shown. HONESTY IS THE BAR, NOT COMPLETENESS: a card that names
              two of three seats and states the third is unlisted passes, which
              is the standard Alexander County already shipped under. Requiring
              a name in every seat would hand the definition to county clerks
              and hold a state open forever on one appointment nobody published.

  MAINTAINED  Every roster file these pages read is rewritten by a SCHEDULED
              workflow. A roster with no job decays silently: the names go
              stale at the speed officeholders change and no gate anywhere
              notices, because every count guard still passes on a file nobody
              is refreshing.

WHAT THIS IS FOR. A state that passes all three switches from expansion to
maintenance — its session stops hunting counties and only tends what ships.
That is an operational consequence, so THE MARK MUST BE ABLE TO GO BACKWARD:
a tranche that adds ten counties without records takes E away again, and this
file is regenerated rather than edited so it does. It is deliberately INTERNAL
— docs and CI, never a reader-facing badge — because publishing it would
promise readers something county publishers can revoke on any given week.

EVERYTHING IS DERIVED BUT ONE TABLE. STATE_COUNTIES is the number of counties
each state has, which changes on a constitutional timescale (the same
justification build_county_status.py gives for owning Illinois's 102). It is
stated rather than counted because every derivable source for it is a coverage
list, and a coverage list as the denominator would make E vacuously true: a
state that serves every county it has bothered to list would always score
100%. The stated number is then CHECKED against the tree, so a typo in it
fails rather than flattering the result.

Usage:
    python3 scripts/build_eam_status.py            # write docs/EAM_STATUS.md
    python3 scripts/build_eam_status.py --check    # CI drift gate
    python3 scripts/build_eam_status.py --report   # print, write nothing
"""

import argparse
import contextlib
import glob
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
WORKFLOW_DIR = os.path.join(REPO_ROOT, ".github", "workflows")
OUT_PATH = os.path.join(REPO_ROOT, "docs", "EAM_STATUS.md")

sys.path.insert(0, HERE)

# The county universe per state. STATED, then checked against the tree below.
# Counted from a coverage list instead, E would measure nothing: a state serves
# every county it has listed, by construction.
STATE_COUNTIES = {"il": 102, "wi": 72, "ia": 99, "mi": 83}

# Instances with no county tier at all. Recorded with a reason rather than
# skipped, because a silently absent row reads as a passing one.
NO_COUNTY_TIER = {
    "ny": "New York City — the instance serves five boroughs, not a county "
          "frontier, so there is no county to examine.",
    "ca": "San Francisco — a consolidated city and county, so the county tier "
          "is the city and there is no frontier.",
}


def fail(msg):
    print("build-eam-status: FAIL — %s" % msg)
    sys.exit(1)


def outline_path(tag):
    if tag == "il":
        return os.path.join(REPO_ROOT, "scripts", "build_metro_outline.py")
    return os.path.join(REPO_ROOT, tag, "scripts", "build_metro_outline.py")


def paren_literal(path, name):
    """The parenthesised literal assigned to `name`, or None.

    Read by balancing parentheses rather than by regex: METRO_COUNTY_FIPS runs
    to dozens of lines with comments between the entries, and a line-anchored
    pattern stops at the first one.
    """
    if not os.path.exists(path):
        return None
    src = open(path, encoding="utf-8").read()
    m = re.search(r"^%s\s*=\s*\(" % re.escape(name), src, re.M)
    if not m:
        return None
    start = m.end() - 1
    depth = 0
    for i in range(start, len(src)):
        if src[i] == "(":
            depth += 1
        elif src[i] == ")":
            depth -= 1
            if depth == 0:
                try:
                    return eval(src[start:i + 1])  # noqa: S307 — our own literal
                except Exception:
                    return None
    return None


def ring_size(tag):
    got = paren_literal(outline_path(tag), "METRO_COUNTY_FIPS")
    return len(got) if got else None


def load_rosters():
    """{tag: {county name: record}} plus {tag: [roster paths read]}.

    Uses build_county_pages' own adapters rather than re-reading the roster
    files, because those adapters are where the shapes are already settled —
    Illinois keys districts to a members list with a per-county extra beside
    it, Wisconsin keys by seat, Iowa joins a chair onto a supervisor, Michigan
    carries a contradicted seat. A second reader of that question is exactly
    the defect this repository keeps rediscovering.
    """
    import build_county_pages as B
    counties, paths = {}, {}
    quiet = io.StringIO()
    with contextlib.redirect_stdout(quiet):
        for inst in B.INSTANCES:
            tag = inst["tag"]
            merged, read = {}, []
            for adapter in inst["adapters"]:
                out, _problems, _nameless, used, _note = getattr(B, adapter)(inst)
                merged.update(out)
                read.extend(used)
            counties[tag] = merged
            paths[tag] = read
    return counties, paths, B


def gap_counties(tag):
    path = os.path.join(REPO_ROOT, tag, "data", "app", "coverage-gaps.json")
    if not os.path.exists(path):
        return set()
    blob = json.load(open(path, encoding="utf-8"))
    records = blob.values() if isinstance(blob, dict) else blob
    out = set()
    for rec in records:
        for slug in rec.get("counties") or []:
            out.add(slug)
    return out


def staged_paths():
    """[(repo-relative path staged, workflow file)] for every scheduled job.

    A workflow counts only if it is BOTH scheduled and stages something. A
    manually-dispatched job is a tool, not maintenance, and a watcher that
    commits nothing is not refreshing anything — both would make M pass on a
    roster no cron ever touches.

    THE STAGED TOKEN IS OFTEN A DIRECTORY, which the first draft of this
    function got wrong and which is why `git add il/data/source` has to be read
    as covering every roster beneath it. Matching whole file paths only, this
    reported seven Illinois GIS rosters as having no job while
    update-il-gis-board-rosters.yml refreshes all seven every Thursday —
    a clean, confident, false answer.
    """
    out = []
    for path in sorted(glob.glob(os.path.join(WORKFLOW_DIR, "*.yml"))):
        text = open(path, encoding="utf-8").read()
        if "schedule:" not in text or "git add " not in text:
            continue
        rel = os.path.relpath(path, REPO_ROOT)
        for line in text.splitlines():
            if "git add " not in line:
                continue
            for token in line.split()[2:]:
                token = token.strip("\"'")
                if token.startswith("-") or "/" not in token:
                    continue
                out.append((token, rel))
    return out


def refreshed_by(rel_path, staged):
    """The scheduled workflows that stage `rel_path`, by file or by directory."""
    hits = []
    for token, workflow in staged:
        if rel_path == token or rel_path.startswith(token.rstrip("/") + "/"):
            hits.append(workflow)
    return sorted(set(hits))


def measure():
    counties, paths, B = load_rosters()
    staged = staged_paths()
    rows = []

    for tag in ("il", "wi", "ia", "mi"):
        total = STATE_COUNTIES[tag]
        ring = ring_size(tag)
        if ring is None:
            fail("%s: no METRO_COUNTY_FIPS in %s — the county universe cannot "
                 "be checked" % (tag, os.path.relpath(outline_path(tag), REPO_ROOT)))
        if ring > total:
            fail("%s: the coverage ring holds %d counties and STATE_COUNTIES "
                 "says the state has %d. One of the two is wrong, and E's "
                 "denominator depends on it." % (tag, ring, total))

        served = {B.slug_of(name) for name in counties.get(tag, {})}
        recorded = gap_counties(tag)
        covered = served | recorded
        unexamined = total - len(covered)

        districts = unanswered = people = 0
        unanswered_names = []
        for name, rec in counties.get(tag, {}).items():
            for d in rec.get("districts") or []:
                districts += 1
                people += sum(1 for m in d.get("members") or []
                              if (m.get("name") or "").strip())
                if not d.get("members") and not d.get("vacancies") and not d.get("note"):
                    unanswered += 1
                    if len(unanswered_names) < 12:
                        unanswered_names.append("%s district %s" % (name, d.get("label")))

        unmaintained = []
        for path in sorted(set(paths.get(tag, ()))):
            rel = os.path.relpath(path, REPO_ROOT)
            if not refreshed_by(rel, staged):
                unmaintained.append(rel)

        rows.append(dict(
            tag=tag, total=total, ring=ring,
            served=len(served), recorded=len(recorded), covered=len(covered),
            unexamined=unexamined,
            districts=districts, people=people,
            unanswered=unanswered, unanswered_names=unanswered_names,
            rosters=len(set(paths.get(tag, ()))), unmaintained=unmaintained,
            E=(unexamined == 0), A=(unanswered == 0),
            M=(not unmaintained),
        ))
    return rows


def letters(row):
    return "".join(L if row[L] else "·" for L in ("E", "A", "M"))


def render(rows):
    out = []
    out.append("# E.A.M. status")
    out.append("")
    out.append("**Generated by `scripts/build_eam_status.py` — never hand-edit.**")
    out.append("`--check` runs in CI. Regenerate after any roster, gap-record or")
    out.append("workflow change.")
    out.append("")
    out.append("A state is **done** when it is Examined, Answered and Maintained,")
    out.append("at which point its session moves from expansion to maintenance. The")
    out.append("mark is computed on every run and **goes backward** the moment a")
    out.append("tranche lands without records, a district stops naming anyone, or a")
    out.append("roster loses its scheduled job.")
    out.append("")
    out.append("Coverage completeness is reported and is deliberately **not** a bar.")
    out.append("Holding a state open until every county ships hands the definition")
    out.append("to county publishers; a county that will never publish a map would")
    out.append("keep a state open forever while telling a reader nothing.")
    out.append("")
    out.append("| state | E.A.M. | counties | examined | districts | named | answered | rosters | maintained |")
    out.append("|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        out.append("| %s | **%s** | %d | %d/%d | %d | %s | %s | %d | %s |" % (
            r["tag"], letters(r), r["total"], r["covered"], r["total"],
            r["districts"], "{:,}".format(r["people"]),
            "all" if r["A"] else "%d short" % r["unanswered"],
            r["rosters"],
            "all" if r["M"] else "%d without a job" % len(r["unmaintained"]),
        ))
    out.append("")
    for tag, why in sorted(NO_COUNTY_TIER.items()):
        out.append("- **%s** — no county tier, so E does not apply. %s" % (tag, why))
    out.append("")

    out.append("## What each state still needs")
    out.append("")
    for r in rows:
        done = r["E"] and r["A"] and r["M"]
        out.append("### %s — %s" % (r["tag"], "**E.A.M.**" if done else letters(r)))
        out.append("")
        if done:
            out.append("Examined, Answered and Maintained. Expansion is finished;")
            out.append("this instance is in maintenance.")
            out.append("")
            continue
        if not r["E"]:
            out.append("- **Examined: no.** %d of %d counties have neither a roster "
                       "nor a gap record naming them. They are not blocked — they "
                       "are unlooked-at, which is the one state this bar refuses."
                       % (r["unexamined"], r["total"]))
        if not r["A"]:
            out.append("- **Answered: no.** %d district(s) name nobody, are not "
                       "marked vacant and carry no note: %s"
                       % (r["unanswered"], "; ".join(r["unanswered_names"])))
        if not r["M"]:
            out.append("- **Maintained: no.** %d roster(s) no scheduled workflow "
                       "rewrites, so their names go stale with nothing reporting "
                       "it: %s" % (len(r["unmaintained"]), ", ".join(r["unmaintained"])))
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="fail if docs/EAM_STATUS.md is not what this run produces")
    ap.add_argument("--report", action="store_true",
                    help="print the table and write nothing")
    args = ap.parse_args()

    rows = measure()
    body = render(rows)

    if args.report:
        print(body)
        return

    if args.check:
        if not os.path.exists(OUT_PATH):
            fail("docs/EAM_STATUS.md is missing — run "
                 "`python3 scripts/build_eam_status.py`")
        if open(OUT_PATH, encoding="utf-8").read() != body:
            fail("docs/EAM_STATUS.md is stale — run "
                 "`python3 scripts/build_eam_status.py`")
    else:
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            f.write(body)

    marks = " ".join("%s=%s" % (r["tag"], letters(r)) for r in rows)
    done = [r["tag"] for r in rows if r["E"] and r["A"] and r["M"]]
    print("build-eam-status: OK — %s; %s" % (
        marks,
        ("in maintenance: " + ", ".join(done)) if done
        else "no instance is E.A.M. yet"))


if __name__ == "__main__":
    main()
