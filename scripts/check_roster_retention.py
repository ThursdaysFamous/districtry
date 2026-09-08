#!/usr/bin/env python3
"""
Retention gate: catch a roster field that quietly stops being published.

WHY THIS EXISTS. Every roster builder in this repo guards a COUNT — "Boone must
seat 12", "Brown must seat 7" — and every one of those guards passed on
2026-08-08 while Brown County's seven published e-mail addresses were one
commit away from being deleted. browncoil.org had switched on Cloudflare's
e-mail obfuscation, so every `mailto:` became `data-cfemail`; the parser read
`mailto:` only and returned seven members with no e-mail at all. Seven rows in,
seven rows out, guard satisfied, contact silently gone from a tool whose entire
purpose is telling residents how to reach their board.

THE GUARDS MEASURED THE WRONG THING. Counting rows says nothing about whether
the rows still carry what they carried yesterday. Thirty of the forty-three
builders do additionally floor a field or two (MIN_EMAILS, MIN_PHONES), which
is better — but each floor is hand-set per county, thirteen builders have none
at all, and NO floor anywhere covers a field nobody thought to name. A new
field ships unguarded by construction.

So this check does not live in the builders. It compares the roster files in
the working tree against the same files at a git ref — usually the PR's base —
and asks one question of every field it finds: does it still appear on about as
many records as it did before? The shipped file is the baseline, so a field
gains protection the moment it first ships, with nothing to configure and no
per-county tuning to drift.

WHAT IT FAILS ON
  * A field that was on >= MIN_PRESENT records and is now on NONE. This is the
    Brown shape, and the one this check was written for.
  * A field that lost at least HALF its records AND at least MIN_ABSOLUTE_DROP
    of them. Turnover moves these numbers by ones and twos; a parser that
    stopped seeing a column moves them by tens.
  * The record count itself collapsing by half — the builders' own province,
    re-checked here for the files whose builder has no floor.

WHAT IT DELIBERATELY IGNORES
  * New files and new fields (nothing to compare against).
  * Small drops. A member leaves, a county drops one phone number: that is the
    world changing, not the pipeline breaking.
  * Files absent from the base ref.

It also refuses to PASS having compared fewer than MIN_FILES_COMPARED files. A
gate that silently checks nothing reports success forever, which is the very
shape of failure it was written to catch — so a bad base ref or a shallow
checkout fails loudly instead of going quietly green.

ACCEPTING A REAL DROP. A consolidated election can legitimately empty a column
for a while. Record it in ACCEPTED_DROPS with a reason and a date rather than
loosening a threshold for everyone — same posture as validate_sources.py's
`blocked` flag.

AND EVERY ACCEPTED ENTRY IS AUDITED AGAINST THE SHIPPED TREE, not only against
the diff. This docstring used to claim an entry "prints a line every run so an
entry cannot rot quietly", and that was false the day after the drop merged:
the entry is consulted only where THIS diff observes the field going away, so
once the drop is on the base branch nothing observes it and the exception goes
silent forever — carrying a permanent hole in the gate's coverage with no line
anywhere saying so. audit_accepted() closes it: every entry is printed on every
run, an entry naming a file that has left the tree FAILS as orphaned, and an
entry whose field is BACK on records FAILS as stale, because an exception that
outlives its reason is a field this gate has quietly stopped watching. Same
property as validate_card_links.py's EXPECTED_UNREACHABLE and
validate_contrast.py's ACCEPTED_SHORTFALLS, which both already had it.

Usage:
    python3 scripts/check_roster_retention.py                  # vs HEAD
    python3 scripts/check_roster_retention.py --base origin/main
    python3 scripts/check_roster_retention.py --report r.md
"""

import argparse
import collections
import json
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# EVERY INSTANCE'S ROSTERS, NOT JUST ILLINOIS'S. This pointed at il/data/app
# alone, and on 2026-08-25 that let through a bot PR which stripped `party`,
# `capitolOffice` and `districtOffice` from ALL 213 New York legislators —
# names only, 63 senators and 150 assemblymembers — while this gate reported
# "222 roster files, no field lost its records" and CI went green. It was
# counting Illinois's files and had never once opened ny/data/app or
# ca/data/app.
#
# That is precisely the failure this gate was built for ("seven rows in, seven
# rows out, guard satisfied, contact gone") happening TO the gate, and it is the
# fifth instance-blind check found in a single day. The directories are
# DISCOVERED from the generator's instance table rather than listed, so a fourth
# instance is covered the day it lands.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from generate_metro_files import INSTANCES
except ImportError:  # pragma: no cover
    INSTANCES = {"il": {"app": "il"}}


def app_data_dirs():
    """(relative, absolute) for every instance roster directory that exists."""
    out = []
    for tag in sorted(INSTANCES):
        rel = os.path.join(INSTANCES[tag]["app"], "data", "app")
        full = os.path.join(REPO_ROOT, rel)
        if os.path.isdir(full):
            out.append((rel, full))
    if not out:  # the pre-R2.3 layout, when the app WAS the repo root
        legacy = os.path.join(REPO_ROOT, "data", "app")
        if os.path.isdir(legacy):
            out.append(("data/app", legacy))
    return out

# A field on a single record is one person's phone number; losing it is
# turnover. Two is where "the source stopped saying this" becomes the more
# likely reading than "two people happened to leave" — it is what makes a
# two-role file like lake-county-board-roles.json protected at all.
MIN_PRESENT = 2
# A halving only fails if it is also this many records, so a 3 -> 1 wobble on a
# tiny board does not cry wolf.
MIN_ABSOLUTE_DROP = 3
RECORD_COLLAPSE_RATIO = 0.5
# Refuse to report success having compared almost nothing — see main().
MIN_FILES_COMPARED = 40

# ---------------------------------------------------------------------------
# Measured, dated exceptions. Key: "<file>:<field>". Value: why, and when it was
# accepted. Keep these rare — each one is a field this check has stopped
# watching, which is exactly what it exists to prevent.
# ---------------------------------------------------------------------------
ACCEPTED_DROPS = {
    # Removed on purpose, 2026-08-28. Every one of the 17 plan 3 counties keyed
    # into this file publishes ONE phone number for its whole board -- measured,
    # exactly one distinct value per county across all 67 districts -- which is
    # the courthouse board office rather than a supervisor's line. The County
    # card had already hoisted that number to a labelled "Board office" row
    # (docs/EXPANSION_GUIDE.md Part 5, the switchboard rule); this file had gone
    # on copying it onto each district, where ONE name renders and nothing on
    # the card contradicts the reading that it is that supervisor's own line.
    # The number still ships, once, county-level, as `boardPhone`. The builder
    # now REFUSES to write if a member row arrives carrying a phone at all, so
    # this is a field that cannot silently come back wrong.
    "ia/data/app/ia-supervisor-members.json:phone":
        "2026-08-28 -- the board switchboard, hoisted to county-level "
        "`boardPhone` and rendered as \"Board office\". It was never a "
        "per-supervisor number; build_ia_supervisor_roster.py now refuses any "
        "phone on a member row.",

    # Palo, Iowa (place GEOID 1961230), removed on purpose 2026-09-05, and NOT
    # because the city stopped publishing -- its council page parses perfectly
    # today. `cityofpalo.com/robots.txt` names six crawlers, allows each of them
    # everything but /admin/ and /manager/, and ends `User-agent: * /
    # Disallow: /`, which refuses this project's agent on every path. The
    # scraper now consults robots.txt before any fetch
    # (`ia/scripts/robots_gate.py`), so the page is never requested and the six
    # officials leave the card. THE ENTRY STAYS IN THE SCRAPER'S TABLE and the
    # check runs weekly, so Palo re-enters by itself if that file changes --
    # at which point this exception goes stale and this gate says so.
    "ia/data/app/ia-city-officials.json:1961230":
        "2026-09-05 -- cityofpalo.com's robots.txt refuses `districtry` on "
        "every path, so the scraper asks before it fetches and never requests "
        "the page. The city still publishes; this project declines to read it.",
}


def records_in(payload):
    """Every dict that looks like a person/place record — one with a name.

    Shape-agnostic on purpose: these files are keyed by district, by county
    slug, by GEOID and by nothing at all, and several nest members two levels
    down. Anything with a `name` is a record, which matched all 58 roster-shaped
    files in data/app when this was calibrated.
    """
    found = []

    def walk(node):
        if isinstance(node, dict):
            if isinstance(node.get("name"), str):
                found.append(node)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(payload)
    return found


def coverage(payload):
    """field -> how many records carry a non-empty value. Plus the record count."""
    recs = records_in(payload)
    counts = collections.Counter()
    for rec in recs:
        for key, value in rec.items():
            if value in (None, "", [], {}):
                continue
            counts[key] += 1
    return counts, len(recs)


# A file pooling more than this many independent sources is checked whole
# rather than per group. Below it, each top-level key is its own source and
# gets its own check; above it (municipal-officials.json pools ~1,500
# municipalities) per-group thresholds would fire on every village that
# reshuffles a page, and the file-level view still shows a systemic loss.
MAX_GROUPS_FOR_PER_GROUP = 200
# A group needs at least this many records before a vanished field there means
# more than one person's details changing.
MIN_GROUP_RECORDS = 3

# ---------------------------------------------------------------------------
# Files whose TOP-LEVEL KEY IS FINER THAN THEIR SOURCE.
#
# The threshold above assumes one top-level key is one source. That holds for
# every file in the fleet but one: wi/data/app/county-board-members.json is
# keyed by SEAT — `<5-digit county GEOID><2-digit district>` — so its 1,591
# keys are 72 counties, and 72 sources landed on the wrong side of a
# 200-source threshold. Lafayette's sixteen rows losing a field read as 16 of
# 1,591 pooled, which is the Brown County shape this whole check was written
# for, one level up.
#
# WHY A NAMED WIDTH RATHER THAN A DERIVED ONE. Nothing in the key says where
# the county ends and the seat begins, and every neighbouring width partitions
# the file too — into groups that are not counties. Measured on the shipped
# file, 2026-09-08:
#
#     width 3 ->    2 groups,   2 of them mixing more than one county
#     width 4 ->   15 groups,  14 of them mixing more than one county
#     width 5 ->   72 groups,   0                             <- counties
#     width 6 ->  201 groups,   0   (past the 200 threshold: no per-group pass)
#     width 7 -> 1591 groups,   0   (one per key: collapses nothing)
#
# A guessed width groups confidently and wrongly, and the two that would MERGE
# counties are the dangerous ones — they read as a working fold. So the width
# is stated, and audit_source_prefixes() re-measures all four properties every
# run against the shipped tree: 2..200 groups, a real collapse, and no group
# holding more than one of the identity values named beside the width.
#
# MENOMINEE IS THE TRAP, AND IT IS A TRAP FOR THE OTHER READING OF THIS KEY.
# That county's joint board seats seven, five by ward and two elected
# countywide, so the file carries `5507801`..`5507805` AND `55078-at-large` —
# six keys for a five-district board. Grouped by the first five characters they
# are one county, which is exactly right HERE, because all six rows come off
# one page in one read and break together. Anyone who reaches for the same
# `key[:5]` to COUNT DISTRICTS gets six for a board that has five. The grouping
# is about which source can fail alone; it is not a district index.
#
# WHY ONLY ONE ENTRY. Measured across all six instances on 2026-09-08: nine
# data/app files pool past the 200-source threshold, and this is the only one
# whose keys are finer than its source. Six are polling-place files keyed by
# place — one county's single publication, not one source per place — and
# il/municipal-officials.json (629) and ia/ia-city-contact.json (939) are
# already one key per source and simply have more than 200, which is the case
# the threshold was written for. The report names the pooled files on every
# run, so a new one of this shape is visible rather than waiting to be noticed.
# ---------------------------------------------------------------------------
# <file> -> (prefix width, the record field that NAMES the source, why)
SOURCE_KEY_PREFIX = {
    "county-board-members.json": (
        5, "county",
        "keyed by seat, `<5-digit county GEOID><2-digit district>` plus "
        "Menominee's `55078-at-large`; the source is the county's own board "
        "page, which all of a county's rows are read from in one fetch"),
}


def groups_of(payload, name=None):
    """{group label -> sub-payload} for a file keyed by county/district, else {}.

    THIS IS THE FIX FOR THE CASE THAT PROMPTED THE WHOLE CHECK. Pooled across a
    file, Brown's seven e-mails vanishing reads as 40 -> 33 in
    il-county-commissioners.json — an 18% dip, under every sane threshold, and
    the first version of this script passed it. Ten counties share that file and
    each is a separate source that can break on its own, so each is measured on
    its own.

    `name` is the file's path; a file in SOURCE_KEY_PREFIX has its keys folded
    to that width first, because there its top-level key is a seat and its
    source is a county.
    """
    if not isinstance(payload, dict):
        return {}
    width = SOURCE_KEY_PREFIX.get(os.path.basename(name or ""), (None,))[0]
    if width:
        folded = {}
        for key, value in payload.items():
            if isinstance(value, (dict, list)) and records_in(value):
                folded.setdefault(key[:width], {})[key] = value
        # Out of band is not silently ignored — audit_source_prefixes() fails
        # the run for it. Returning {} here only decides what this one
        # comparison does while that failure is being printed.
        if folded and len(folded) <= MAX_GROUPS_FOR_PER_GROUP:
            return folded
        return {}
    groups = {key: value for key, value in payload.items()
              if isinstance(value, (dict, list)) and records_in(value)}
    if not groups or len(groups) > MAX_GROUPS_FOR_PER_GROUP:
        return {}
    return groups


def group_name(sub):
    """What a group calls itself, or None — for a label a reader can act on.

    These files are keyed by FIPS, so `55065` alone sends nobody anywhere. The
    name sits on the record for a one-key group and one level down for a folded
    one, and both shapes are read here so the caller does not have to know which
    it has.
    """
    if not isinstance(sub, dict):
        return None
    if isinstance(sub.get("county"), str):
        return sub["county"]
    for value in sub.values():
        if isinstance(value, dict) and isinstance(value.get("county"), str):
            return value["county"]
    return None


def audit_source_prefixes():
    """Findings for SOURCE_KEY_PREFIX itself: (severity, key, message).

    Same property as audit_accepted(): the table is checked against the SHIPPED
    TREE on every run, so an entry cannot quietly stop meaning anything. Three
    ways it can rot, all of them silent without this:

      * the file leaves the fleet, and the entry goes on naming it;
      * the file is re-keyed one key per source, so the fold collapses nothing
        and the entry is doing no work while looking as though it is;
      * the file grows past the threshold even folded, so the fold no longer
        buys per-group measurement and groups_of() falls back to whole-file —
        which is the exact silence this entry exists to end.

    Reported per instance, because a sibling can ship a file of the same name.
    """
    out = []
    for base in sorted(SOURCE_KEY_PREFIX):
        width, identity, why = SOURCE_KEY_PREFIX[base]
        seen = 0
        for rel_dir, data_dir in app_data_dirs():
            full = os.path.join(data_dir, base)
            if not os.path.isfile(full):
                continue
            seen += 1
            label = "%s/%s" % (rel_dir, base)
            try:
                with open(full, encoding="utf-8") as f:
                    payload = json.load(f)
            except (ValueError, OSError) as e:
                out.append(("FAIL", label, "does not read as JSON (%s)." % e))
                continue
            keys = [k for k, v in payload.items()
                    if isinstance(v, (dict, list)) and records_in(v)] \
                if isinstance(payload, dict) else []
            folded = sorted({k[:width] for k in keys})
            if not keys:
                out.append(("FAIL", label, "has no record-carrying top-level keys, "
                                           "so folding them to %d characters "
                                           "groups nothing." % width))
            elif len(folded) == len(keys):
                out.append(("FAIL", label, "folds %d keys to %d groups at width %d "
                                           "— it collapses nothing, so the file is "
                                           "already one key per source and this "
                                           "entry does no work. Delete it."
                            % (len(keys), len(folded), width)))
            elif len(folded) < 2:
                out.append(("FAIL", label, "folds %d keys to a single group at "
                                           "width %d, which separates no sources "
                                           "at all — that is the whole-file view "
                                           "under another name." % (len(keys), width)))
            elif len(folded) > MAX_GROUPS_FOR_PER_GROUP:
                out.append(("FAIL", label, "folds %d keys to %d groups at width %d, "
                                           "past the %d-source threshold, so the "
                                           "fold no longer buys per-group "
                                           "measurement and the file is back to "
                                           "being checked whole."
                            % (len(keys), len(folded), width,
                               MAX_GROUPS_FOR_PER_GROUP)))
            else:
                # THE BRANCH THE OTHER THREE CANNOT SEE. A width that is too
                # NARROW merges distinct sources and still lands inside the
                # band: width 4 gives 15 groups, 14 of which hold more than one
                # county, and every arithmetic check above passes it. A merged
                # group is worse than no grouping — it pools two publishers and
                # calls the result a source — so the fold has to prove it split
                # the file along the same line the records name themselves by.
                merged = []
                for pref in folded:
                    sub = {k: v for k, v in payload.items() if k[:width] == pref}
                    seen_ids = {rec.get(identity) for rec in records_in(sub)
                                if isinstance(rec.get(identity), str)}
                    if len(seen_ids) > 1:
                        merged.append("%s = %s" % (pref, ", ".join(sorted(seen_ids))))
                named = sum(1 for pref in folded
                            if any(isinstance(rec.get(identity), str)
                                   for rec in records_in(
                                       {k: v for k, v in payload.items()
                                        if k[:width] == pref})))
                if merged:
                    out.append(("FAIL", label,
                                "folds %d keys to %d groups at width %d, but %d "
                                "of those groups hold more than one `%s` — the "
                                "width is too narrow and is pooling separate "
                                "sources: %s"
                                % (len(keys), len(folded), width, len(merged),
                                   identity, "; ".join(merged[:4]))))
                elif not named:
                    out.append(("FAIL", label,
                                "folds %d keys to %d groups at width %d, but no "
                                "record carries `%s`, so nothing can check that "
                                "the fold splits the file along its own sources."
                                % (len(keys), len(folded), width, identity)))
                else:
                    sizes = collections.Counter(k[:width] for k in keys)
                    out.append(("OK-folded", label,
                                "%d keys -> %d sources at width %d (%d..%d rows "
                                "each), each holding exactly one `%s`: %s"
                                % (len(keys), len(folded), width,
                                   min(sizes.values()), max(sizes.values()),
                                   identity, why)))
        if not seen:
            out.append(("FAIL", base, "is not shipped by any instance. The entry "
                                      "has outlived its file — delete it. "
                                      "Recorded: %s" % why))
    return out


def audit_accepted():
    """Findings for the exception list itself: (severity, key, message).

    An accepted drop is read ONLY where a diff shows the field disappearing, so
    the moment the drop is merged the entry stops being consulted and stops
    being printed. That is a gate measuring less than it claims with nothing
    saying so, which is the failure this whole file exists to catch, happening
    to its own exception list. So the list is checked against what is ACTUALLY
    SHIPPED: the file must still be there, and the field must still be gone.
    """
    out = []
    for key in sorted(ACCEPTED_DROPS):
        why = ACCEPTED_DROPS[key]
        parts = key.split(":")
        if len(parts) < 2 or not parts[0].endswith(".json"):
            out.append(("FAIL", key, "is not in the form `<instance>/data/app/"
                                     "<file>.json:<field>` (or `:<group>:<field>`), "
                                     "so nothing can check it."))
            continue
        label, rest = parts[0], parts[1:]
        full = os.path.join(REPO_ROOT, label)
        if not os.path.isfile(full):
            out.append(("FAIL", key, "names `%s`, which is not in the tree. The "
                                     "exception has outlived its file — delete it."
                        % label))
            continue
        try:
            with open(full, encoding="utf-8") as f:
                payload = json.load(f)
        except (ValueError, OSError) as e:
            out.append(("FAIL", key, "names `%s`, which does not read as JSON (%s)."
                        % (label, e)))
            continue
        counts, _ = coverage(payload)
        groups = groups_of(payload, label)
        back = None
        if len(rest) == 1:
            name = rest[0]
            if counts.get(name, 0) >= MIN_PRESENT:
                back = ("the field `%s` is back on %d record(s)"
                        % (name, counts[name]))
            elif name in groups and len(records_in(groups[name])) >= MIN_PRESENT:
                back = ("the source `%s` is back with %d record(s)"
                        % (name, len(records_in(groups[name]))))
        else:
            group, field = rest[0], rest[1]
            if group not in groups:
                # Unlike the two-part shape, this one is unambiguous: a group
                # that is gone makes the entry unevaluable forever, so it is a
                # dead exception rather than a field still legitimately absent.
                out.append(("FAIL", key, "names the source `%s` in `%s`, which "
                                         "that file no longer has. The exception "
                                         "can never be evaluated again — delete "
                                         "it. Recorded: %s" % (group, label, why)))
                continue
            sub, _ = coverage(groups[group])
            if sub.get(field, 0) >= MIN_PRESENT:
                back = ("`%s` is back on %d of %s's record(s)"
                        % (field, sub[field], group))
        if back:
            out.append(("FAIL", key, "is STALE — %s. Retire the entry so the gate "
                                     "watches the field again; a fix must remove "
                                     "its exception. Recorded: %s" % (back, why)))
        else:
            out.append(("OK-accepted", key, why))
    return out


# Where the roster files live in a commit, newest layout first. The app moved
# into an instance folder (il/) in R2.3, so a PR opened after the move compares
# against a base that may predate it. Git reads a TREE at the base ref — it
# cannot follow a rename or a symlink — so the base lookup has to try both, or
# every file reads as "absent at the base", every file lands in `skipped`, and
# the vacuity guard below fails every PR with the wrong diagnosis (it would say
# "shallow clone"). The move PR itself passes either way; the breakage would
# have arrived on the NEXT PR, which is the worst possible timing.
# Fallbacks for a file whose directory MOVED between the base ref and now — the
# R2.3 root-to-il/ move is the reason this list exists. Tried after the file's
# own directory, never instead of it.
APP_REL_DIRS = ("il/data/app", "data/app")


def git_show(ref, name, rel_dir_first=None):
    """The roster's content at `ref`, or None if it is not there under any
    known layout. `rel_dir_first` is the directory the file lives in NOW, so a
    sibling instance's roster is looked up where it actually is rather than
    under Illinois's path.

    The R2.3 fallbacks apply ONLY to Illinois's lineage: il/data/app is the
    directory that moved (from the repo root), so only a file living there now
    may be looked up under its old home. Any other instance's file absent at
    the base is genuinely NEW — falling through would compare it against
    Illinois's same-named file, which is exactly what happened the day the
    fourth instance landed: wi's brand-new 8-district congress-roster.json
    resolved against IL's 17 at the base and read as a roster collapse."""
    if rel_dir_first is None or rel_dir_first in APP_REL_DIRS:
        candidates = ([rel_dir_first] if rel_dir_first else []) + [
            d for d in APP_REL_DIRS if d != rel_dir_first]
    else:
        candidates = [rel_dir_first]
    for rel_dir in candidates:
        try:
            out = subprocess.run(["git", "show", "%s:%s/%s" % (ref, rel_dir, name)],
                                 cwd=REPO_ROOT, capture_output=True, check=False)
        except OSError as e:
            raise SystemExit("check-roster-retention: cannot run git (%s)" % e)
        if out.returncode != 0:
            continue
        try:
            return json.loads(out.stdout.decode("utf-8"))
        except ValueError:
            return None
    return None


def compare(name, old, new):
    """Findings for one file. Each is (severity, message)."""
    out = []
    old_counts, old_recs = coverage(old)
    new_counts, new_recs = coverage(new)

    if old_recs >= MIN_ABSOLUTE_DROP and new_recs < old_recs * RECORD_COLLAPSE_RATIO:
        out.append(("FAIL", "record count fell %d -> %d (more than half). The "
                            "builder's own count guard should have caught this — "
                            "check that it ran." % (old_recs, new_recs)))

    for field, was in sorted(old_counts.items()):
        now = new_counts.get(field, 0)
        if now >= was:
            continue
        accepted = ACCEPTED_DROPS.get("%s:%s" % (name, field))
        lost = was - now
        if now == 0 and was >= MIN_PRESENT:
            msg = ("`%s` VANISHED — was on %d of %d records, now on none. This is "
                   "the shape of a source that changed how it publishes the field, "
                   "not of people leaving. Check the page before accepting it."
                   % (field, was, old_recs))
            out.append(("OK-accepted" if accepted else "FAIL",
                        msg + (" ACCEPTED: %s" % accepted if accepted else "")))
        elif lost >= MIN_ABSOLUTE_DROP and now <= was * 0.5:
            msg = ("`%s` lost %d of %d records (now %d) — at least half. Turnover "
                   "moves these by ones and twos." % (field, lost, was, now))
            out.append(("OK-accepted" if accepted else "FAIL",
                        msg + (" ACCEPTED: %s" % accepted if accepted else "")))

    # Per-source pass: one broken county inside a shared file is invisible in
    # the totals above, which is exactly how the first draft of this script
    # waved Brown through.
    old_groups, new_groups = groups_of(old, name), groups_of(new, name)
    for label, old_sub in sorted(old_groups.items()):
        new_sub = new_groups.get(label)
        if new_sub is None:
            # A WHOLE SOURCE LEAVING THE FILE IS THE LOUDEST THING THAT CAN
            # HAPPEN TO IT, and this branch used to say "not this check's call"
            # and move on. Nothing else was checking either: a per-county
            # builder's floor is sized for the FILE (Iowa's is 12 counties of
            # 17), so one county dropping out clears it, the field-coverage
            # pass above never sees a group that is gone, and the record-count
            # test needs a halving. On 2026-08-29 a bot PR deleted all five of
            # Grundy County's supervisors that way — green everywhere, and the
            # county's own page was up the whole time, still naming them; a
            # single failed fetch in one weekly run was the whole cause.
            #
            # A county that genuinely stops publishing is a real event and gets
            # an ACCEPTED_DROPS entry with a reason and a date, exactly like a
            # field that stops being published. What it does not get is silence.
            _, lost_recs = coverage(old_sub)
            if lost_recs < MIN_PRESENT:
                continue                  # a one-record group: turnover, not a source
            accepted = ACCEPTED_DROPS.get("%s:%s" % (name, label))
            # These files are keyed by FIPS, so the label alone is a number
            # nobody can act on. Where the group names itself, say the name.
            named = group_name(old_sub)
            label = "%s (%s)" % (label, named) if named else label
            msg = ("%s VANISHED from this file — it had %d record(s) at the base "
                   "and has none now, while the rest of the file is unchanged. A "
                   "source that stops publishing is a real event; a source that "
                   "failed to fetch once is not. GO AND LOOK AT THE PAGE before "
                   "accepting this." % (label, lost_recs))
            out.append(("OK-accepted" if accepted else "FAIL",
                        msg + (" ACCEPTED: %s" % accepted if accepted else "")))
            continue
        sub_old, sub_old_recs = coverage(old_sub)
        sub_new, _ = coverage(new_sub)
        if sub_old_recs < MIN_GROUP_RECORDS:
            continue
        for field, was in sorted(sub_old.items()):
            if sub_new.get(field, 0) or was < MIN_PRESENT:
                continue
            accepted = ACCEPTED_DROPS.get("%s:%s:%s" % (name, label, field)) \
                or ACCEPTED_DROPS.get("%s:%s" % (name, field))
            # The EXCEPTION KEY is the raw label and the MESSAGE is the named
            # one: `55065` is what an ACCEPTED_DROPS entry has to be written
            # against and is not something a reader can act on, so the county
            # names itself in the sentence and nowhere else. Getting these the
            # same way round would either send a reader to a number or make the
            # exception key move when a publisher renames a county.
            named = group_name(old_sub)
            shown = "%s (%s)" % (label, named) if named else label
            msg = ("`%s` VANISHED for %s — was on %d of that group's %d records, "
                   "now on none, while the rest of the file is unchanged. That is "
                   "one source changing how it publishes, which the file-wide "
                   "totals hide." % (field, shown, was, sub_old_recs))
            out.append(("OK-accepted" if accepted else "FAIL",
                        msg + (" ACCEPTED: %s" % accepted if accepted else "")))
    return out, old_recs, new_recs


def main():
    ap = argparse.ArgumentParser(
        description="Fail when a roster field stops being published.")
    ap.add_argument("--base", default="HEAD",
                    help="git ref to compare against (default HEAD)")
    ap.add_argument("--report", metavar="PATH", help="also write a markdown report")
    args = ap.parse_args()

    findings, checked, skipped, pooled = [], 0, [], []
    scanned_dirs = app_data_dirs()
    for rel_dir, data_dir in scanned_dirs:
      for path in sorted(os.listdir(data_dir)):
        if not path.endswith(".json"):
            continue
        full = os.path.join(data_dir, path)
        try:
            with open(full, encoding="utf-8") as f:
                new = json.load(f)
        except (ValueError, OSError):
            continue
        recs = records_in(new)
        if not recs:
            continue                      # geometry-only file: nothing to retain
        # WHICH FILES ARE STILL MEASURED WHOLE, collected in the scan that has
        # already loaded this file rather than in a second pass over data/app
        # (which cost 3.6s of a 7.3s run when it was written that way). The
        # threshold's interesting question is not whether 200 is right but
        # which files sit above it: one whose keys are FINER than its source
        # belongs in SOURCE_KEY_PREFIX, and nothing surfaces that until
        # somebody reads a list. This is that list, printed every run.
        sources = len([k for k, v in new.items()
                       if isinstance(v, (dict, list)) and records_in(v)]) \
            if isinstance(new, dict) else 0
        if (path not in SOURCE_KEY_PREFIX
                and sources > MAX_GROUPS_FOR_PER_GROUP):
            pooled.append(("%s/%s" % (rel_dir, path), len(recs), sources))
        old = git_show(args.base, path, rel_dir)
        if old is None:
            skipped.append(path)          # new file, or absent at the base ref
            continue
        checked += 1
        # Reported with its directory: two instances can ship a file of the
        # same name (congress-roster.json is in all three), and a finding that
        # does not say WHICH one sends a reader to the wrong file.
        label = "%s/%s" % (rel_dir, path)
        rows, old_recs, new_recs = compare(label, old, new)
        for sev, msg in rows:
            findings.append((sev, label, msg))

    # A gate that compares NOTHING passes every time, which is the exact shape
    # of failure this whole check exists to catch — so it refuses to be vacuous.
    # Reached by a bad --base, a wrong working directory, or a shallow checkout
    # where `git show <base>:<path>` finds nothing; all three look like success
    # otherwise. The floor is deliberately well under the ~160 rosters that
    # exist, so it fires on "the comparison broke" rather than on normal growth.
    if checked < MIN_FILES_COMPARED:
        print("check-roster-retention: FAIL — compared only %d roster files against "
              "%s (expected at least %d). Nothing was verified. Usually a base ref "
              "the checkout does not have: this needs real history, not a shallow "
              "clone. %s" % (checked, args.base, MIN_FILES_COMPARED,
                             "%d file(s) had no counterpart at that ref." % len(skipped)
                             if skipped else ""), file=sys.stderr)
        sys.exit(1)

    # The exception list is audited against the SHIPPED tree, so an entry keeps
    # printing (and can start failing) long after the diff that recorded it.
    findings += [(sev, key, msg) for sev, key, msg in audit_accepted()]
    # Same reason, one level up: SOURCE_KEY_PREFIX decides HOW a file is
    # grouped, and an entry that has stopped grouping anything is a per-source
    # check silently back to being a per-file one.
    findings += [(sev, key, msg) for sev, key, msg in audit_source_prefixes()]

    fails = [f for f in findings if f[0] == "FAIL"]
    accepted = [f for f in findings if f[0] == "OK-accepted"]
    folded = [f for f in findings if f[0] == "OK-folded"]

    lines = ["# Roster field retention", "",
             "Compared %d roster files against `%s`." % (checked, args.base)]
    if skipped:
        lines.append("New since that ref (nothing to compare): %s."
                     % ", ".join("`%s`" % s for s in skipped))
    lines.append("")
    if fails:
        lines += ["## FAIL (%d)" % len(fails), ""]
        lines += ["- **%s** — %s" % (p, m) for _, p, m in fails] + [""]
    if accepted:
        lines += ["## Accepted drops (%d)" % len(accepted), "",
                  "Recorded in `ACCEPTED_DROPS`, and re-checked against the "
                  "shipped tree on every run. Each is a field this check has "
                  "stopped watching — read them now and then, and retire any "
                  "whose reason has passed.", ""]
        lines += ["- **%s** — %s" % (p, m) for _, p, m in accepted] + [""]
    if folded:
        lines += ["## Keys folded to their source (%d)" % len(folded), "",
                  "Files whose top-level key is finer than the source that can "
                  "break alone, folded per `SOURCE_KEY_PREFIX` and re-measured "
                  "against the shipped tree on every run.", ""]
        lines += ["- **%s** — %s" % (p, m) for _, p, m in folded] + [""]
    if pooled:
        lines += ["## Measured whole (%d)" % len(pooled), "",
                  "More than %d sources in one file, so a per-source pass would "
                  "fire on ordinary churn. Listed every run because a file whose "
                  "keys are FINER than its source belongs in `SOURCE_KEY_PREFIX` "
                  "and is invisible here until somebody reads this list."
                  % MAX_GROUPS_FOR_PER_GROUP, ""]
        lines += ["- `%s` — %d records across %d top-level keys" % row
                  for row in pooled] + [""]
    if not fails and not accepted:
        lines += ["Every field still appears on about as many records as before.", ""]
    elif not fails:
        lines += ["Every field still appears on about as many records as before, "
                  "apart from the accepted drops above.", ""]
    report = "\n".join(lines).rstrip() + "\n"

    sys.stdout.write(report)
    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            f.write(report)

    if fails:
        print("check-roster-retention: FAIL — %d field(s) stopped being published "
              "or carry a stale exception" % len(fails), file=sys.stderr)
        sys.exit(1)
    print("check-roster-retention: OK — %d roster files, no field lost its records "
          "(%d accepted drop(s) and %d folded key(s), each re-checked against the "
          "shipped tree; %d file(s) measured whole)"
          % (checked, len(accepted), len(folded), len(pooled)))


if __name__ == "__main__":
    main()
