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

              AN INSTANCE WHOSE COUNTY DISTRICTS ARE NOT DRAWN YET passes on the
              third branch, through the records that say so, and the report says
              "by record" rather than "all" — publishing "all" over a tier that
              draws nothing is a stronger sentence than the tree supports, and
              the distinction is the same one this report already makes between
              a watched file and a rewritten one.

  MAINTAINED  Every data file THE APP READS is under a stated plan — a
              SCHEDULED job that REWRITES it, a SCHEDULED WATCHER on its
              source, or a WATCH.md row that names it and states WHEN it is
              re-checked. A file under none of those decays silently, because
              every count guard still passes on one nobody is refreshing.
              The watch file is `<tag>/WATCH.md` for five instances and the
              REPO ROOT's for Illinois, which has none of its own and never
              did — see WATCH_FILE.

              THE SURFACE IS THE APP'S, NOT THE PAGES'. The first version
              measured only the roster files the per-county pages read, and
              Wisconsin found the hole that leaves: it flagged a 72-record
              directory of seat counts and MISSED
              county-supervisory-districts.json — 1,590 districts, 4.6 MB, the
              file the whole county-board card is drawn on, and the file the
              directory is derived from (`seats` is `max(SUPERID)` read back
              off it). A bar that fails a restatement and passes its source is
              not measuring what it claims to.

              A WATCH.md ROW COUNTS AND IS NOT A LOOPHOLE, because boundaries
              do not move weekly and a weekly job on them would be a
              guaranteed no-op. What the row must carry is a WHEN — a cadence,
              or a trigger. Wisconsin's supervisory boundaries are filed with
              LTSB on 15 January and 15 July by statute; that is the clock,
              and a row saying so is a plan. A filename sitting in prose is a
              mention, and the difference is the whole reason this clause can
              be allowed.

              AND THAT SENTENCE WAS THE RULE WHILE THE CODE DID NOT ENFORCE IT,
              found by the Minnesota thread on 2026-10-01. Every WATCH.md
              carries several tables and only some are cadence tables; the rest
              lead with a prose SUBJECT — blockers, open questions, deliberate
              omissions. Reading the first cell alone for a cadence word meant
              every long row in those tables counted as a plan for whatever file
              it happened to name, so Minnesota's narrative about another
              state's negative point and its record of a coordinate sweep were
              read as plans for four files neither row is about. Minnesota had
              SIX files with no plan, not five. The table's own first-column
              header decides now, against a declared set of time words
              (`is_schedule_table`), and the fix immediately found its own
              opposite: a BLANK LINE inside Illinois's exposure-class table had
              read as the end of that table, dropping the four real plans in the
              rows after it and taking the one instance that passes all three
              tests down to two. A headerless fragment is a CONTINUATION; prose
              or a heading is what ends a table. Re-scored across all eight live
              instances, no state's mark moves and only Minnesota's count does —
              which is worth saying plainly, because a stricter reading that
              changed nothing anywhere would have been the tell that it was not
              reading anything.

              THE WATCHER CASE IS NOT A LOOPHOLE AND WAS LEARNED THE HARD WAY.
              Mason County's roster is transcribed BY HAND on purpose: its
              source is a scanned PDF whose text layer extracts as noise that
              PARSES rather than failing, so a scraper would not error, it
              would ship confident garbage under real officeholders' names.
              watch-mason-roster-source.yml checks weekly that the county still
              links that exact PDF and that its bytes still hash the same, and
              opens an issue when either moves. That is maintenance — the
              output is a request for a person rather than a diff — and a bar
              that only counted `git add` called it unmaintained and would have
              sent somebody to build the very scraper that workflow's own
              comment warns against.

              A WATCHER IS READ FROM THE WORKFLOW AND NOT FROM THE SCRIPT IT
              RUNS, and that is a BOUNDED UNDERSTATEMENT rather than an
              oversight. Raised by the Kentucky thread, 2026-10-01: its monthly
              source check names its files one level down, inside the script,
              so `watched_by` does not see them and the report credits it with
              nothing. Reading one level in would find them — and would also
              credit every instance's monthly `validate_sources.py`, whose
              manifest names most of the boundary files in the fleet, which
              would turn a REACHABILITY check into a maintenance plan for
              geometry across six states at once. That script proves a source
              still answers and a built file is still present; it does not
              notice a boundary being redrawn, and a floor on a feature count
              cannot either. So nothing is widened here on this module's own
              authority: the understatement is recorded, and whether a monthly
              reachability check counts as a plan for a map is a question for
              the operator rather than a regex.

              Both kinds are reported, and the report SAYS WHICH, because
              watched is a weaker guarantee than rewritten: a watcher tells you
              the source moved, and a person still has to act. The report also
              distinguishes what a file holds. A file naming PEOPLE goes stale
              at the speed officeholders change; a file of structure — seat
              counts and county URLs — decays far more slowly, on
              reapportionment and link rot. The first draft justified this bar
              by officeholder churn alone and then reported a Wisconsin file
              holding no people at all, which is a measure whose stated reason
              does not match its own finding.

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
import ast
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

# ONE READER FOR WHICH INSTANCES ARE LIVE. `validate_instance_registration`
# already holds metros.json, the tree and the deploy's own excludes together on
# every pull request, so reading its two functions means a state reaches this
# report on the commit that publishes it and no table here has to be remembered.
from build_coverage_gaps import (  # noqa: E402  (ONE reader of the gaps block)
    ASK, ASK_OUTCOMES, ASK_SILENCE_DAYS, COVERS, load_gaps)
from validate_instance_registration import (  # noqa: E402  (FLEET_SHARED)
    dark_instances, discovered_instances,
)

# The county universe per state. STATED, then checked against the tree below.
# Counted from a coverage list instead, E would measure nothing: a state serves
# every county it has listed, by construction.
STATE_COUNTIES = {"il": 102, "wi": 72, "ia": 99, "mi": 83, "mn": 87,
                  "ky": 120, "ny": 62, "in": 92}

# Instances with no county tier at all. Recorded with a reason rather than
# skipped, because a silently absent row reads as a passing one.
#
# NEW YORK IS SCORED AS A STATEWIDE APP ON ALL FOUR TESTS SINCE 2026-10-01, and
# the reading it replaces is kept here because this file's convention is to put
# a superseded reading under its correction rather than delete it. That reading
# ran: "the instance's subject is New York City; its county frontier is not the
# state's 62, and scoring E against that number would hand the New York thread a
# 62-county obligation on the strength of a bookkeeping change rather than a
# decision." The missing piece was the decision, and it has been taken by the
# thread that bears the obligation: New York asked for all four tests to score
# it statewide, having first MEASURED the tier it was asking to be held to —
# #1328 records what 57 county front pages outside the city publish, and what
# they do not. So E and A now use the state's own 62 and C's separate
# COVERED_COUNTIES entry is no longer a divergence. San Francisco stays a city
# app, because a consolidated city and county has no county above it.
NO_COUNTY_TIER = {
    "ca": "San Francisco — a consolidated city and county, so the county tier "
          "is the city and there is no frontier.",
}


def fail(msg):
    print("build-eam-status: FAIL — %s" % msg)
    sys.exit(1)


def live_instances():
    """Every instance tag the deploy publishes, in tag order.

    DERIVED, NEVER LISTED, and that is the whole of this change. The first
    version iterated the tuple ("il", "wi", "ia", "mi"), so Minnesota and
    Kentucky — live since 2026-09-30 — were scored by nobody and nothing said
    so: an absent row reads exactly like a row with no findings, which is the
    failure mode this module already records three times over in its own
    docstrings. New York and San Francisco fared worse than absent; they got a
    one-line note and no Maintained reading at all, on the two instances whose
    files are the least watched in the fleet.

    So the fleet is read rather than restated, and a go-live PR joins its state
    to this report with nothing here to edit. `check_county_universe()` is the
    other half: a newly published state with no entry in STATE_COUNTIES and no
    entry in NO_COUNTY_TIER FAILS, naming the tag and both ways to clear it,
    because the alternative is a state that silently scores nothing.
    """
    live = sorted(discovered_instances() - dark_instances())
    if len(live) < 2:
        fail("found %d live instance(s) (%s). The fleet reader has broken, and "
             "a short list reads as a fleet with nothing to report."
             % (len(live), ", ".join(live) or "none"))
    return live


def check_county_universe(live):
    """Every live instance states its county universe or why it has none."""
    unstated = [t for t in live
                if t not in STATE_COUNTIES and t not in NO_COUNTY_TIER]
    if unstated:
        fail("%s now published and this report cannot score Examined for "
             "%s: add the state's county count to STATE_COUNTIES, or record in "
             "NO_COUNTY_TIER why a county frontier is not this instance's "
             "subject. Either is one line; neither can be guessed from the tree, "
             "because every derivable source for the number is a coverage list "
             "and a coverage list as the denominator makes Examined vacuous."
             % (", ".join(unstated), "it" if len(unstated) == 1 else "them"))
    stale = [t for t in sorted(set(STATE_COUNTIES) | set(NO_COUNTY_TIER))
             if t not in live]
    if stale:
        fail("%s is named in STATE_COUNTIES or NO_COUNTY_TIER and is not a live "
             "instance. Drop the entry, or publish the instance."
             % ", ".join(stale))


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
                    # literal_eval, never eval: this reads another script's
                    # source, and `eval` made `validate_python_hygiene.py`
                    # skip its whole-file name check — on the one file in
                    # this repo that has been wrong five times.
                    return ast.literal_eval(src[start:i + 1])
                except (ValueError, SyntaxError):
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


# A record naming a PERSON carries one of these beside its name. The list is
# what the fleet's own rosters publish; it is deliberately short, because the
# question is only "does this file name people", never "who".
PERSON_FIELDS = ("email", "phone", "party", "role", "title", "term",
                 "profileUrl", "vacant")

# A RECORD CAN NAME A PERSON WITHOUT A FIELD CALLED `name`, and reading only
# that one key published a false claim about the whole fleet. Found by the
# Wisconsin thread, 2026-10-01: its 72 town-clerk directories name a clerk for
# all 1,847 Wisconsin municipalities and a deputy for 639 of them, under the keys
# `clerk` and `deputyClerk`, so every one of those files was reported as
# reference data and the benchmark's headline — that not one unplanned file names
# a person — was wrong. Iowa's county-board chairs are the same shape under
# `chair`.
#
# THE ROLE KEY IS ITS OWN EVIDENCE, which is why these do not need the
# PERSON_FIELDS corroboration that `name` does. `name` is ambiguous — a
# polygon's label, a library building, an education agency — and this module has
# already published 12,654 imaginary people by trusting it alone. `clerk` is not
# ambiguous: an organisation has a telephone and does not have a chair.
#
# STATED, AND THE STATEMENT IS GATED. Each key below is measured on a named file
# in this tree, and `check_undeclared_name_keys()` sweeps every `data/app` record
# for a role-shaped key holding a string and FAILS on one that is not declared
# here — so the next state to ship `auditor` or `treasurer` is told to declare
# it rather than being read as reference data. A key ending in `Url` is excluded
# there by its value, not by its name: `membersUrl` and `clerkUrl` are the two
# in the tree today and both hold a link.
ROLE_NAME_KEYS = (
    # key, the file it is measured on, what it holds
    ("clerk", "wi/data/app/town-clerks-001.json", "the municipal clerk"),
    ("deputyClerk", "wi/data/app/town-clerks-001.json", "the deputy clerk"),
    ("chair", "ia/data/app/ia-county-board-chairs.json",
     "the county board chair — this file carries no email, phone or term, so "
     "the PERSON_FIELDS test alone reads 43 named chairs as reference data"),
    ("president", "il/data/app/school-board-members.json",
     "the Chicago Board of Education's president, found by the sweep below on "
     "its first run"),
)
NAME_KEYS = ("name",) + tuple(k for k, _, _ in ROLE_NAME_KEYS)


def _records(obj, depth=0):
    """Every dict inside a roster, at any nesting the fleet actually uses."""
    if depth > 6:
        return
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            for x in _records(v, depth + 1):
                yield x
    elif isinstance(obj, list):
        for v in obj:
            for x in _records(v, depth + 1):
                yield x


def names_in(rec):
    """How many people this record names.

    COUNTED, NOT A BOOLEAN, because a Wisconsin clerk record names two: a clerk
    and a deputy. Returning 1 per record would report 1,847 people where the
    files hold 2,486, and the figure is what decides whether a report line reads
    "no officeholder is going stale here".
    """
    n = 0
    if (rec.get("name") or "").strip() if isinstance(rec.get("name"), str) \
            else False:
        if any(f in rec for f in PERSON_FIELDS):
            n += 1
    elif "name" in rec and any(f in rec for f in PERSON_FIELDS):
        # A name that is present and not a plain string — the fleet's nested
        # shapes put a list under it — still counts the record once.
        n += 1
    for key, _file, _what in ROLE_NAME_KEYS:
        v = rec.get(key)
        if isinstance(v, str) and is_name_shaped(v):
            n += 1
    return n


def is_name_shaped(value):
    """True when this string is shaped like a person's name.

    ONE READER, used by `names_in` to count people and by
    `check_undeclared_name_keys` to decide what it is looking at. Two tests of
    one question is where this repository's recurring defect starts, and here it
    would mean the gate demanding a key be declared for a value the counter then
    refuses to count.
    """
    value = (value or "").strip()
    return bool(value and not URLISH.search(value)
                and NAME_SHAPED.match(value)
                and 2 <= len(value.split()) <= 6)


def shape_of(path):
    """(kind, n) for a data file: geometry, roster or structure.

    CORRECTED 2026-09-22, and the defect is worth keeping in view because this
    module's report is what four sessions read. This counted `"name"` in the
    raw bytes and called the answer PEOPLE. A GeoJSON feature's
    `properties.name` is a polygon's label, so `mi-precincts.json` was
    published as naming 3,895 people and `adams-county-outline.json` as naming
    1, each with the sentence "they go stale at the speed that board turns
    over" attached to a boundary that moves once a decade. Measured on the
    shipped tree the day it was fixed: 171 report lines claimed a person
    count, 12,654 people in total, and EVERY ONE was wrong — 169 GeoJSON
    FeatureCollections plus two polling-place files whose names are buildings.
    An OVERSTATEMENT misroutes work exactly as an understatement does: it
    sends a session to build a weekly job for a file that needs none.

    The three shapes are read off the file instead:

      geometry   a FeatureCollection. Names nobody; rots on reapportionment.
      roster     a record carrying a name and one of PERSON_FIELDS.
      structure  neither — seat counts, addresses, links.

    That a FeatureCollection never names a person is MEASURED, not assumed:
    CLAUDE.md records seven Illinois counties whose members ride the same GIS
    feature as the boundary, so the case is real. It does not reach
    `data/app` today, and `check_geometry_names_nobody()` re-measures that on
    every run rather than trusting this sentence.
    """
    rel = os.path.relpath(path, REPO_ROOT)
    if os.path.isdir(path):
        kind = PREFIX_KIND.get(rel.replace(os.sep, "/") + "/")
        if not kind:
            fail("%s is a directory on the surface with no PREFIX_CLASSES "
                 "entry, so its kind would be guessed." % rel)
        return (kind, len(glob.glob(os.path.join(path, "*.json"))))
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError):
        return ("structure", 0)
    if isinstance(doc, dict) and doc.get("type") == "FeatureCollection":
        return ("geometry", len(doc.get("features") or []))
    people = sum(names_in(rec) for rec in _records(doc))
    return ("roster", people) if people else ("structure", 0)


# The gate below asks a DIFFERENT question from `shape_of` and therefore uses a
# different test, which is deliberate rather than the duplication this repo
# usually warns about. `shape_of` asks "does this file name people", where a
# `name` beside an `email` or a `phone` is a roster: measured on the shipped
# tree, narrowing PERSON_FIELDS to the two lists below would reclassify 14 real
# rosters as structure — Wisconsin's 134 alderpersons, Illinois's 101 county
# clerks, six county boards. The gate asks "is a BOUNDARY FEATURE naming a
# person", where those two fields prove nothing, because an organisation has a
# telephone: `ia-aeas.json` (nine education agencies) and `library-sites.json`
# (482 library buildings) both carry name + phone and name nobody. Both were
# flagged by the broad list on the gate's own first run.
PERSON_ONLY_FIELDS = ("party", "term", "vacant", "role", "profileUrl")

# Matched as whole keys, never as substrings: `FirePD` contains "rep" and
# `supervisorial_district` contains "supervisor", and a substring test reported
# both as officeholders.
ROLE_KEYS = frozenset("""member official chair chairman supervisor
commissioner alderman alderperson trustee president mayor clerk judge
incumbent officeholder representative rep""".split())


# Each case is (path, expected kind, why this file settles it). The files are
# named because a shape is only real in a file — and each is re-read from the
# tree, so a case naming a file that has LEFT the tree fails rather than
# quietly stopping being checked, the property `ACCEPTED_DROPS` had to be
# given after the fact.
# (value, is it a person's name, why). Every string here is one the sweep met in
# the tree, or the shape it had to be taught to refuse.
NAME_SHAPE_CASES = (
    ("Terri L Horacek", True, "a Wisconsin town clerk"),
    ("Sean B. Harden", True, "the Chicago school board's president — a period"),
    ("Miranda Christensen", True, "two words is the floor"),
    ("Mary-Kate O'Brien", True, "a hyphen and an apostrophe"),
    ("(217) 277-2150", False, "`clerkPhone` — digits"),
    ("PLAN 3", False, "`supervisorPlan` — a plan code"),
    ("TRANSITIONING", False,
     "`supervisorPlan` again, and THE case that forced the two-word floor: one "
     "all-letter word passes every other test here"),
    ("the county directory lists 4, and Iowa Code 331.201 allows only 3 or 5",
     False, "`supervisorsWithheld` — a sentence"),
    ("https://adamscounty.iowa.gov/supervisors/", False, "a link"),
    ("townofadamswi.gov", False, "a bare hostname, which has no scheme to catch"),
    ("", False, "empty"),
)


def check_name_shapes():
    bad = 0
    for value, want, why in NAME_SHAPE_CASES:
        got = is_name_shaped(value)
        if got != want:
            bad += 1
            print("  NAME  %-56r want=%s got=%s  (%s)"
                  % (value[:56], want, got, why))
    print("  NAME  %d value case(s), %d names / %d refused"
          % (len(NAME_SHAPE_CASES), sum(1 for c in NAME_SHAPE_CASES if c[1]),
             sum(1 for c in NAME_SHAPE_CASES if not c[1])))
    return bad


SHAPE_CASES = (
    ("il/data/app/adams-county-outline.json", "geometry",
     "one polygon whose only property is its own label — the exact file the "
     "old reader published as naming 1 person"),
    ("mi/data/app/mi-precincts.json", "geometry",
     "3,895 polygons; the old reader published 3,895 people"),
    ("wi/data/app/library-sites.json", "geometry",
     "482 library buildings carrying name + phone: an organisation's "
     "telephone is not a person"),
    ("ia/data/app/ia-aeas.json", "geometry",
     "nine education agencies, likewise name + phone"),
    ("wi/data/app/madison-polling-places.json", "structure",
     "137 buildings with a name and an address and no person"),
    ("il/data/app/boone-fire-districts.json", "geometry",
     "six polygons whose only property is a district number — the old "
     "reader called this 'structure (seat counts, county links)', which it "
     "carries neither of"),
    ("il/data/app/il-county-commissioners.json", "roster",
     "a real roster: people under counties"),
    ("il/data/app/congress-roster.json", "roster",
     "a real roster keyed by district"),
    ("wi/data/app/county-board-members.json", "roster",
     "783 supervisors, the fleet's largest roster keyed by seat"),
    ("il/data/app/il-county-clerks.json", "roster",
     "101 clerks carrying name + email only, which is why PERSON_FIELDS "
     "cannot be narrowed to the person-only list the gate uses"),
    ("wi/data/app/town-clerks-001.json", "roster",
     "a clerk and often a deputy per municipality under `clerk` and "
     "`deputyClerk` and no `name` key at all — 72 of these files were reported "
     "as reference data, which is what made the benchmark's headline wrong"),
    ("ia/data/app/ia-county-board-chairs.json", "roster",
     "43 chairs under `chair`, with no email, phone or term beside them, so "
     "the role key has to be its own evidence"),
    ("ia/data/app/ia-county-officers.json", "roster",
     "`supervisorPlan` holds PLAN 1 and TRANSITIONING in the same file as real "
     "officers: the record is a roster and the plan is not a person"),
)


# (E, A, M, letters, done, why). A test that does not APPLY is None and must
# never render like one that FAILED: `..M` for San Francisco reads as an instance
# failing two bars when it is answering the only one it has, and `is_done` has to
# treat the dash as satisfied or no city instance could ever be done.
MARK_CASES = (
    (True, True, True, True, "EAMC", True, "every bar met"),
    (True, True, False, True, "EA\u00b7C", False, "M outstanding"),
    (False, True, True, True, "\u00b7AMC", False,
     "a tranche landed without records"),
    (True, True, True, False, "EAM\u00b7", False,
     "every state today: the fourth test is the one nothing passes yet"),
    (None, None, True, False, "--M\u00b7", False,
     "a city instance: E and A are the wrong question, and C is still a bar"),
    (None, None, True, True, "--MC", True,
     "a city instance with every test it is asked met"),
    (None, None, False, False, "--\u00b7\u00b7", False, "nothing met"),
    (None, True, True, True, "-AMC", True, "mixed, for completeness"),
)


def check_marks():
    bad = 0
    for E_, A_, M_, C_, want, want_done, why in MARK_CASES:
        row = {"E": E_, "A": A_, "M": M_, "C": C_}
        got, got_done = letters(row), is_done(row)
        if got != want or got_done != want_done:
            bad += 1
            print("  MARK  E=%-5s A=%-5s M=%-5s C=%-5s want=%s/%s got=%s/%s  (%s)"
                  % (E_, A_, M_, C_, want, want_done, got, got_done, why))
    print("  MARK  %d mark case(s), %d done / %d not"
          % (len(MARK_CASES), sum(1 for c in MARK_CASES if c[5]),
             sum(1 for c in MARK_CASES if not c[5])))
    return bad


def check_live_fleet():
    """The fleet reader answers the published instances and nothing else.

    Held against the tree rather than a list, so this case cannot be the thing
    it is checking. What it CAN catch is the two failures that made this change
    necessary: a dark folder scored as though it served readers, and a published
    instance missing from the report with nothing saying so.
    """
    bad = 0
    live, dark = set(live_instances()), dark_instances()
    overlap = sorted(live & dark)
    if overlap:
        bad += 1
        print("  FLEET %s is both published and blanket-excluded from the "
              "deploy" % ", ".join(overlap))
    for tag in sorted(live):
        if not os.path.exists(os.path.join(REPO_ROOT, tag, "sw.js")):
            bad += 1
            print("  FLEET %s is published and ships no sw.js, so its "
                  "Maintained surface would read as empty" % tag)
    unscored = sorted(live - set(STATE_COUNTIES) - set(NO_COUNTY_TIER))
    if unscored:
        bad += 1
        print("  FLEET %s is published and this report scores no Examined for "
              "it" % ", ".join(unscored))
    print("  FLEET %d published instance(s): %s; %d dark: %s"
          % (len(live), ", ".join(sorted(live)), len(dark),
             ", ".join(sorted(dark)) or "none"))
    return bad


# (tag, filename, is it planned, why this case is here). Both halves of the
# table-header rule, held to the two real files that forced it. A check on only
# the refusals would pass a reader that credits nothing, and a check on only the
# credits would pass the lenient reader this replaced.
WATCH_TABLE_CASES = (
    ("mn", "fleet-outlines.json", False,
     "named in passing by a blockers row about ANOTHER state's negative point. "
     "That table leads with a prose subject, not a cadence"),
    ("mn", "metros.json", False, "named by a row recording a coordinate sweep"),
    ("il", "metro-outline.json", True,
     "a real plan, in a row that sits after a BLANK LINE inside its own "
     "exposure-class table — the continuation case"),
    ("il", "coverage-gaps.json", True, "the last row of that same continuation"),
    ("il", "early-voting-sites.json", True,
     "a plan in an ordinary `Cadence | What` table, so it holds whichever way "
     "the continuation rule goes"),
)


def check_watch_tables():
    """Hold the table-header rule to real rows in real WATCH.md files."""
    bad = 0
    for tag, name, want, why in WATCH_TABLE_CASES:
        got = name in watch_rows(tag)[0]
        if got != want:
            bad += 1
            print("  WATCH %-4s %-32s want=%s got=%s  (%s)"
                  % (tag, name, want, got, why))
    print("  WATCH %d watch-row case(s), %d planned / %d not"
          % (len(WATCH_TABLE_CASES),
             sum(1 for _, _, w, _ in WATCH_TABLE_CASES if w),
             sum(1 for _, _, w, _ in WATCH_TABLE_CASES if not w)))
    return bad


def selftest():
    """Hold `shape_of` to files whose shape is settled.

    This module's own record says it was corrected four times on the day it
    was built and had no self-test that would have caught any of them. The
    fifth correction was the classifier, so the classifier gets one.
    """
    bad = check_marks() + check_live_fleet() + check_name_shapes()
    bad += check_watch_tables() + check_named_unit() + check_ask_credit()
    for head, want, why in HEADER_CASES:
        got = is_schedule_table([head])
        if got != want:
            bad += 1
            print("  HEAD  %-20s want=%s got=%s  (%s)" % (head, want, got, why))
    print("  HEAD  %d table-header case(s), %d schedules / %d not"
          % (len(HEADER_CASES), sum(1 for _, w, _ in HEADER_CASES if w),
             sum(1 for _, w, _ in HEADER_CASES if not w)))
    for cell, want, why in WHEN_CASES:
        got = states_a_when(cell)
        if got != want:
            bad += 1
            print("  WHEN  %-58s want=%s got=%s  (%s)"
                  % (cell[:58], want, got, why))
    print("  WHEN  %d cadence-cell case(s), %d accepted / %d refused"
          % (len(WHEN_CASES), sum(1 for _, w, _ in WHEN_CASES if w),
             sum(1 for _, w, _ in WHEN_CASES if not w)))
    for rel, want, why in SHAPE_CASES:
        path = os.path.join(REPO_ROOT, rel)
        if not os.path.exists(path):
            print("  ORPHAN %s — the case has left the tree; name another "
                  "file of the same shape" % rel)
            bad += 1
            continue
        got, n = shape_of(path)
        mark = "ok" if got == want else "WRONG"
        if got != want:
            bad += 1
        print("  %-5s %-52s %-9s n=%-5d %s"
              % (mark, rel, got, n, why if got == want
                 else "expected %s" % want))
    if bad:
        fail("%d case(s) failed" % bad)
    print("build-eam-status: selftest OK — %d shape case(s), %d cadence cell(s), "
          "%d table header(s), %d watch row(s), %d mark case(s), "
          "%d name-value case(s), %d unit-roster case(s), "
          "%d ask-credit case(s)"
          % (len(SHAPE_CASES), len(WHEN_CASES), len(HEADER_CASES),
             len(WATCH_TABLE_CASES), len(MARK_CASES), len(NAME_SHAPE_CASES),
             len(NAMED_UNIT_CASES), len(ASK_CREDIT_CASES)))


def check_geometry_names_nobody():
    """FAIL if a shipped FeatureCollection starts naming people.

    `shape_of` calls every FeatureCollection nameless. That is true of the
    tree today and is not true by construction — CLAUDE.md records seven
    Illinois counties whose members ride the same GIS feature as the
    boundary, so a roster arriving inside a FeatureCollection is a shape this
    fleet already produces. It does not reach `data/app` today; if one did,
    the report would go on calling a roster a boundary and nothing would say
    so. Measured on the shipped tree: zero features flagged.
    """
    stems = {r.rstrip("s") for r in ROLE_KEYS}
    bad = []
    for inst in sorted(glob.glob(os.path.join(REPO_ROOT, "*", "data", "app"))):
        for path in sorted(glob.glob(os.path.join(inst, "*.json"))):
            try:
                with open(path, encoding="utf-8") as fh:
                    doc = json.load(fh)
            except (OSError, ValueError):
                continue
            if not (isinstance(doc, dict)
                    and doc.get("type") == "FeatureCollection"):
                continue
            for feat in doc.get("features") or []:
                props = feat.get("properties") or {}
                why = []
                if "name" in props:
                    why += [f for f in PERSON_ONLY_FIELDS if f in props]
                why += [k for k in props
                        if k.strip().lower().rstrip("s_0123456789") in stems]
                if why:
                    bad.append("%s (%s)" % (os.path.relpath(path, REPO_ROOT),
                                            ", ".join(sorted(set(why)))))
                    break
    if bad:
        fail("a shipped FeatureCollection names people, so shape_of would "
             "report it as a boundary: %s. Teach shape_of to read it, or "
             "move the roster into its own file." % "; ".join(sorted(set(bad))))


# Matched on a key's own words, so `membersUrl` and `clerkUrl` are reached and
# then excluded BY THEIR VALUE: both hold a link, and a URL is not a name.
ROLE_WORD = re.compile(r"[a-z]+")
# WHAT A PERSON'S NAME LOOKS LIKE, measured on what the sweep below turned up
# rather than imagined. A role-shaped key is not enough on its own: the tree
# carries `clerkPhone` holding "(217) 277-2150", `supervisorPlan` holding
# "PLAN 3" and `supervisorsWithheld` holding a sentence of explanation, and all
# three would be counted as officeholders by the key alone. So the VALUE has to
# be name-shaped — letters and the punctuation names carry, no digits, at most
# six words, AND AT LEAST TWO — which keeps the three out and lets "Terri L
# Horacek" and "Sean B. Harden" through. A URL is excluded first, for
# `membersUrl` and `clerkUrl`.
#
# TWO WORDS IS WHAT SEPARATES A NAME FROM A STATUS, and the value that forced it
# is `supervisorPlan`'s "TRANSITIONING" — one all-letter word, which every other
# test here accepts. Every officeholder in every roster this fleet ships carries
# a forename and a surname, so the floor costs nothing today. THE COST IT WOULD
# HAVE is a mononym: a one-word name would be read as a status and counted as
# nobody, and the sweep below would not flag it either, because it applies the
# same test. Stated rather than left to be discovered.
URLISH = re.compile(r"(?i)^(https?:|//|www\.)|\.(gov|com|org|net|us|edu)\b")
NAME_SHAPED = re.compile(r"^[A-Za-z][A-Za-z .'\u2019-]{1,58}$")


def role_shaped_keys(rec):
    """Keys in this record whose own words name an office and whose value is a
    person-shaped string."""
    stems = {r.rstrip("s") for r in ROLE_KEYS}
    out = []
    for key, value in rec.items():
        if not isinstance(value, str) or not value.strip():
            continue
        value = value.strip()
        if not is_name_shaped(value):
            continue
        words = ROLE_WORD.findall(re.sub(r"(?<!^)(?=[A-Z])", "_", key).lower())
        if any(w.rstrip("s") in stems for w in words):
            out.append(key)
    return out


def check_undeclared_name_keys():
    """FAIL when a shipped record names a person under a key nobody declared.

    `names_in` reads a STATED list of keys, and a stated list goes stale: the
    whole reason this gate exists is that `name` alone was stated and 2,486
    Wisconsin clerks and deputies went uncounted for as long as the report
    existed, which made its headline finding — that no unplanned file names a
    person — false. The next state to publish `auditor` or `treasurer` would do
    the same silently, so the tree is swept for the shape rather than trusted to
    match the list.
    """
    declared = set(NAME_KEYS)
    found = {}
    for inst in sorted(glob.glob(os.path.join(REPO_ROOT, "*", "data", "app"))):
        for path in sorted(glob.glob(os.path.join(inst, "*.json"))):
            try:
                with open(path, encoding="utf-8") as fh:
                    doc = json.load(fh)
            except (OSError, ValueError):
                continue
            for rec in _records(doc):
                for key in role_shaped_keys(rec):
                    if key not in declared:
                        found.setdefault(key, set()).add(
                            os.path.relpath(path, REPO_ROOT))
    if found:
        fail("a shipped record names somebody under a key this report does not "
             "read, so the file would be reported as reference data: %s. Add "
             "the key to ROLE_NAME_KEYS with the file it is measured on, or "
             "rename the field."
             % "; ".join("`%s` (%s%s)"
                         % (k, sorted(v)[0],
                            "" if len(v) == 1 else " and %d more" % (len(v) - 1))
                         for k, v in sorted(found.items())))


def gap_counties(tag):
    """(county slugs named one by one, ids of records covering the whole state).

    TWO ANSWERS BECAUSE THE FILE MAKES TWO DIFFERENT CLAIMS. A `counties` tag is
    a promise the Data gaps panel can locate that county, which is why
    build_coverage_gaps.py refuses one with no shipped outline. `everyCounty`
    says the record accounts for every county in the state, which is what
    EXAMINED is actually asking, and costs no outlines because it locates
    nothing.

    Read through the tags alone, Minnesota scored 0 of 87 counties examined and
    Kentucky 0 of 120, while each publishes a record reading "all 87 counties" /
    "all 120 counties" with a measured reason. That answer is false, and it
    points the wrong way: it would send a state to ship 87 county outlines to
    move a bookkeeping number, when the outlines exist for a reader's panel that
    would have nothing to show there.

    Both are returned and both are reported, so a statewide declaration cannot
    stand in for county-by-county work without the difference being printed.
    """
    path = os.path.join(REPO_ROOT, tag, "data", "app", "coverage-gaps.json")
    if not os.path.exists(path):
        return set(), []
    blob = json.load(open(path, encoding="utf-8"))
    records = blob.values() if isinstance(blob, dict) else blob
    out, statewide = set(), []
    for rec in records:
        for slug in rec.get("counties") or []:
            out.add(slug)
        if rec.get("everyCounty"):
            statewide.append(rec.get("id") or "<unnamed record>")
    return out, sorted(statewide)


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
    """The scheduled workflows that stage `rel_path`, by file or by directory.

    THE MATCH RUNS BOTH WAYS because a surface entry can itself be a folder
    (PREFIX_CLASSES). A workflow that stages `il/data/app/` refreshes a class
    under it, and a workflow that stages one file inside the class refreshes the
    class — testing only the first direction would report a folder as
    unrefreshed while a job rewrote its contents every week.
    """
    hits = []
    for token, workflow in staged:
        if (rel_path == token
                or rel_path.startswith(token.rstrip("/") + "/")
                or (rel_path.endswith("/") and token.startswith(rel_path))):
            hits.append(workflow)
    return sorted(set(hits))


def watcher_texts():
    """[(workflow rel path, text)] for every scheduled job that can open an issue.

    Read once. A watcher names the file, runs on a schedule, and commits
    nothing, which is the point: where a source cannot be re-read safely by
    machine, the honest output is a request for a person. Requiring `git add`
    alone reads that deliberate design as neglect.
    """
    out = []
    for path in sorted(glob.glob(os.path.join(WORKFLOW_DIR, "*.yml"))):
        text = open(path, encoding="utf-8").read()
        if "schedule:" in text and "issues: write" in text:
            out.append((os.path.relpath(path, REPO_ROOT), text))
    return out


def watched_by(rel_path, watchers=None):
    """The scheduled watchers naming `rel_path`.

    A folder class is searched for with AND without its trailing slash: this
    module writes `il/data/app/population/` and a workflow naming the same
    folder is as likely to write it bare.
    """
    if watchers is None:
        watchers = watcher_texts()
    forms = {rel_path, rel_path.rstrip("/")}
    return sorted({rel for rel, text in watchers
                   if any(f in text for f in forms)})


# A WATCH.md row counts only if it states WHEN. A cadence or a trigger is a
# plan; a filename sitting in prose is a mention, and the difference is the
# whole reason this clause is not a loophole.
#
# THE FIRST VOCABULARY HELD ONLY INTERVAL WORDS AND REJECTED THE CLEAREST
# CADENCE IN THE FLEET. Wisconsin's supervisory row reads "Shortly after 15
# January and 15 July" — the statutory LTSB filing dates, which is a harder
# commitment than "semiannual" because it names the days — and the regex
# matched none of it. A CALENDAR DATE IS A CADENCE, so month names count.
WHEN = re.compile(r"(?i)\b(dail|week|month|quarter|semiannual|semi-annual|annual|"
                  r"year|decenn|census|any change|on a change|20\d\d-\d\d-\d\d|"
                  r"january|february|march|april|may|june|july|august|september|"
                  r"october|november|december)")

# A row whose cadence cell points at the row above ("Same windows", "Same run")
# INHERITS that row's when. Grouping rows under one cadence is how a reader
# writes a table, and refusing it would push an author into repeating a
# statutory date on every line — or, worse, into inventing a different-looking
# cadence to satisfy a gate. It only ever inherits from a row that itself
# stated a when, so a table of nothing but back-references still counts for
# nothing.
SAME_AS_ABOVE = re.compile(r"(?i)^\W*same\b")


# A ROW CAN ONLY STATE A SCHEDULE IF ITS TABLE IS A SCHEDULE, AND READING THE
# FIRST CELL ALONE IS WHAT GOT THIS WRONG. Every WATCH.md carries several
# tables, and only some of them are cadence tables: the rest are blockers
# (`What | Why it cannot wait | Last done`), open questions (`Question | Why it
# is open | What would close it`) and deliberate omissions (`What | Why it was
# left, and what it costs a reader | Last done`). Their first column is a
# SUBJECT, written as prose — and prose about a boundary or an election matches
# the cadence vocabulary readily, so every long row in those tables read as a
# plan for whatever file it happened to mention. Measured on `mn/WATCH.md`: four
# files were credited by two rows, one a narrative about another state's
# negative point and one a record of a coordinate sweep, neither of them a plan
# for anything. Minnesota had six files with no plan, not five.
#
# So the table's own header decides, and the header words are DECLARED rather
# than guessed at from the shape of the cell: measured across all eight live
# instances' files, the first column is one of `Cadence`, `When`, `Date` or
# `Edition` in every cadence table and one of `What` or `Question` in every
# table that is not one. A header this does not know is treated as NOT a
# schedule, so a new table shape reads as unplanned — visible as files short of
# a plan — rather than silently crediting its rows.
TIME_HEADERS = ("cadence", "when", "date", "edition")


def is_schedule_table(header_cells):
    """True when this table's first column commits each row to a time."""
    first = (header_cells[0] if header_cells else "").strip().strip("*").lower()
    return first in TIME_HEADERS

# A DATE IS A WHEN, AND ONLY WHERE THE CELL LEADS WITH IT (Adam's ruling,
# 2026-09-25: "widen the vocabulary to accept a date"). A year — with or without
# a quarter or a range — is a MORE specific commitment than `annually`, and
# rejecting it forced a row to be worded vaguer than what the project actually
# knows: the root WATCH.md's `**2029 Q4**`, `**2031 Q2**`, `**2031–2032**` and
# `**2032–2033**` are all real plans, and the identical set is in `ny/WATCH.md`
# and `ca/WATCH.md`, so this is a fleet rule that reaches only `il` today
# because the report reads four instances.
#
# ANCHORED AT THE START OF THE CELL, `**` AND ALL, BECAUSE A BARE `\b20\d\d\b`
# IS TOO LOOSE AND THE CELL IT BREAKS IS NAMED: `ia/WATCH.md` line 53 reads
# "Iowa specifically, no fixed cadence (the Legislature's own ArcGIS org has
# already revised this boundary once, mid-2026, ...)" — a cell that states
# outright that it has NO cadence, which a year matched anywhere inside it would
# silently promote to a plan. The date has to be the cell's OWN commitment
# rather than a numeral somewhere in its prose, and that Iowa cell still failing
# is the negative test this clause is worth nothing without. `WHEN_CASES` below
# ships it, with the five other phrases that must keep failing.
WHEN_DATE = re.compile(r"^\W*20\d\d\b")


def states_a_when(cell):
    """True when a cadence cell commits to a time, by vocabulary or by date."""
    return bool(WHEN.search(cell) or WHEN_DATE.match(cell))


# (cell, should it count as a when, why this case is here). Each is a REAL cell
# from a WATCH.md in this tree or a phrase the ruling deliberately leaves out.
WHEN_CASES = (
    ("**2029 Q4**", True, "root WATCH.md's pre-cycle dry read — a date, no vocabulary word"),
    ("**2031 Q2**", True, "P.L. 94-171 delivery; the same cell is in ny/ and ca/"),
    ("**2031\u20132032**", True, "a RANGE is still the cell's own commitment"),
    ("**2032\u20132033**", True, "municipal remaps"),
    ("**2031**, when TIGERweb publishes 2030 census blocks", True,
     "matched twice over — the anchored date and the word census"),
    ("Iowa specifically, no fixed cadence (the Legislature's own ArcGIS org has "
     "already revised this boundary once, mid-2026, ...)", False,
     "THE negative test, and the cell that forced WHEN_DATE to be anchored: it "
     "says outright that it has no cadence, and a year matched anywhere inside "
     "it would promote that to a plan. It was ia/WATCH.md line 53 when this case "
     "was written; the Iowa thread is replacing that row with one that names "
     "real dates, so the string is kept here as the shape to refuse rather than "
     "as a cell to go looking for"),
    ("Rolling, post-enactment", False, "states a trigger shape, not a when"),
    ("Per-body, ad hoc", False, "ad hoc is the absence of a cadence"),
    ("Ad hoc", False, "same, standing alone"),
    ("no fixed cadence", False, "says so in words"),
    ("Before each election", False,
     "an election has no fixed date; a row wanting this names the months"),
    ("Every PR, by CI", False,
     "a gate is not a cadence — and a --check proves a file matches its inputs, "
     "never that the inputs are current"),
)


# (first header cell, is it a schedule table, why this case is here). Every one
# is a REAL header row from a WATCH.md in this tree, read 2026-10-01 across all
# eight live instances — the refused ones being the tables whose rows were
# counted as plans before this reader existed.
HEADER_CASES = (
    ("Cadence", True, "the weekly-jobs table at the top of all eight files"),
    ("When", True, "the runbook and post-election tables"),
    ("Date", True, "il's and ca's trigger tables"),
    ("Edition", True, "il's CPS attendance-dataset roll"),
    ("What", False,
     "THE negative test. mn's and ky's blockers table, mn's deliberate "
     "omissions, ia's and ky's open-questions tables all lead with a prose "
     "SUBJECT, and prose about a boundary or an election matches the cadence "
     "vocabulary readily — which is how two mn rows, one about another state's "
     "negative point and one a coordinate sweep, were read as plans for four "
     "files neither row is about"),
    ("Question", False, "mi's open-questions table; a question is not a clock"),
    ("Trigger", False,
     "a real header, but never a FIRST column — it is il's and ca's second. "
     "Refused here so the set cannot be widened by a word that happens to "
     "appear in a header somewhere"),
    ("", False, "a separator with no header above it credits nothing"),
)


# ILLINOIS'S WATCH FILE IS THE ROOT ONE, and reading `<tag>/WATCH.md` for
# every state meant reading NOTHING for the instance that carries most of the
# fleet's files. Five instances ship `<tag>/WATCH.md`; Illinois does not and
# never did, because it was the only instance when that file was written, so
# its rows — the CPS attendance-dataset drill, the district-search index, the
# LTSB filing — sit at the repo root. The instrument therefore reported every
# Illinois file as unplanned whether or not a row named it, and no gate could
# see the difference: an empty `planned_rows` is what a state with no plans
# looks like. Keyed by tag rather than by "root if the per-tag file is absent",
# so a new instance that forgets its WATCH.md reads as having none rather than
# silently inheriting Illinois's.
WATCH_FILE = {"il": "WATCH.md"}


# A CLASS ROW NAMES A PATTERN, BECAUSE A ROW CANNOT NAME 101 FILES. Illinois
# carries 101 `<county>-county-outline.json`, 79 library-district files and 46
# precinct layers, and every file in each of those sets has ONE clock — the
# TIGER vintage roll, an annexation, a re-precincting. Writing them out would
# be 234 lines restating three facts, which is the shape this report exists to
# replace, so a row may name its class as a glob inside backticks.
#
# THREE THINGS KEEP IT FROM BECOMING A BLANKET. The glob must be written
# `*-<suffix>.json` in backticks, so prose cannot match by accident and a bare
# `*.json` is not expressible. The suffix must be at least six characters, so
# `*-x.json` cannot stand in for everything. And `measure()` FAILS when one
# pattern covers more than a third of an instance's surface, because a single
# cadence claimed over that many files is a statement about several different
# clocks — fire, park, library and board districts do not move together — and
# prints every pattern's match count on each run so a widening one is visible
# before it reaches that ceiling.
CLASS_GLOB = re.compile(r"`\*-([A-Za-z0-9_-]{6,}\.json)`")


def watch_rows(tag):
    """({filename: cadence}, [(pattern, cadence)]) for rows that state a when."""
    path = os.path.join(REPO_ROOT, WATCH_FILE.get(tag, os.path.join(tag, "WATCH.md")))
    if not os.path.exists(path):
        return {}, []
    out, globs, last_when = {}, [], None
    # The header is the row BEFORE the `|---|` separator, so each row is held
    # until the separator says whether the table it opened is a schedule.
    pending, schedule = None, False
    for line in open(path, encoding="utf-8"):
        if not line.lstrip().startswith("|"):
            # A BLANK LINE DOES NOT END THE TABLE, and reading it as one cost
            # Illinois its mark. `WATCH.md`'s exposure-class table has a blank
            # line in the middle of it, for breathing room — the three rows
            # after it carry no header of their own, so resetting there read
            # them as a headerless table and dropped the plans for
            # `metro-outline.json`, `il-state-outline.json`,
            # `il-county-board-offices.json` and `coverage-gaps.json`. A
            # fragment with no header and no separator of its own is a
            # CONTINUATION; what genuinely ends a table is prose or a heading,
            # and a real new table re-establishes the verdict with its own
            # header and separator anyway.
            if line.strip():
                pending, schedule, last_when = None, False, None
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells:
            continue
        if set(cells[0]) <= set("-: "):
            schedule = is_schedule_table(pending or [])
            last_when = None
            continue
        pending = cells
        if not schedule:
            continue
        when = None
        if states_a_when(cells[0]):
            when = cells[0]
            last_when = when
        elif SAME_AS_ABOVE.match(cells[0]) and last_when:
            when = "%s (%s)" % (cells[0], last_when)
        if not when:
            continue
        for suffix in CLASS_GLOB.findall(line):
            globs.append((re.compile(r"^[A-Za-z0-9_-]+-%s$" % re.escape(suffix)),
                          "*-" + suffix, when))
        for name in re.findall(r"[A-Za-z0-9_.-]+\.json", line):
            out.setdefault(name, when)
        # A FOLDER CLASS CARRIES NO FILENAME, so the `.json` scan above cannot
        # see it and a row written for one would count for nothing while
        # looking exactly like a plan. Matched on the class's own rel path,
        # with or without its trailing slash.
        for rel in PREFIX_KIND:
            if rel in line or rel.rstrip("/") in line:
                out.setdefault(rel, when)
    return out, globs


# THE APP'S OWN STATEMENT OF WHICH FILES IT FETCHES IS `sw.js`, AND THE
# INSTRUMENT USED TO RE-DERIVE IT WRONG. The first version kept every
# `<tag>/data/app/*.json` whose BASENAME appears in that instance's
# `index.html`, and three of Illinois's loaders build their URL by
# concatenation — `"data/app/" + slug + "-county-outline.json"` — so no literal
# ever appears for the file they fetch. Measured 2026-09-25, that filter missed
# 86 of Illinois's 388 files, 215 of Wisconsin's 262, 24 of Iowa's 57, 31 of
# Michigan's 53, 5 of New York's 25 and 1 of San Francisco's 14. The files it
# dropped are not marginal: Wisconsin's whole per-county polling-place set and
# Illinois's county outlines, the geometry the gaps panel tests a pin against.
#
# A RUNTIME SLUG CAN COME FROM A DATA FILE, which is why no amount of reading
# the app more cleverly would have fixed this. The gaps panel draws any county
# whose outline ships, and the slugs it asks for come from `coverage-gaps.json`
# — so eight Illinois outlines (Bureau, Champaign, Fayette, Jasper, Lawrence,
# Marion, Piatt, Pope) are fetched for counties no layer serves, and "no code
# path in index.html can produce this name" is not a conclusion a grep of
# index.html can reach. That reading cost this module a false "dead files"
# finding before it was caught by reading the loader.
#
# So ask the app. `sw.js` splits `data/app` in two — cache-first geometry and
# network-first rosters — and every instance's own `validate_index.py` fails
# when a `data/app` file is in neither list or in both, so the two lists ARE
# the directory, held equal per instance by a gate that runs on every PR.
# `validate_index.py` is also the honest reader of the question this filter was
# badly answering: it checks the literal reference and carries
# DYNAMIC_REFERENCE, 98 files each with a note saying which slug builds its
# URL. Nothing here re-derives that. The worksheet's `data_files` and a bare
# glob of the directory both give the same 388 today, and the three agree
# because each link in the chain is gated; `sw.js` is read rather than either
# because it is the app's statement about its own fetches rather than an
# authoring surface or an inventory of a folder.
SW_LIST = re.compile(r"const (GEOMETRY_URLS|ROSTER_URLS) = \[(.*?)\n\];", re.S)
SW_ENTRY = re.compile(r'"\./(data/app/[^"/]+\.json)"')


def app_data_files(tag):
    """Every flat `<tag>/data/app/*.json` the instance's own sw.js fetches."""
    path = os.path.join(REPO_ROOT, tag, "sw.js")
    if not os.path.exists(path):
        return []
    src = open(path, encoding="utf-8").read()
    found, out = set(), []
    for name, body in SW_LIST.findall(src):
        found.add(name)
        out += ["%s/%s" % (tag, u) for u in SW_ENTRY.findall(body)]
    # A READER THAT SILENTLY MATCHES NOTHING IS THE FAILURE THIS MODULE IS
    # FIXING, one level up: `robots_policy` answered "no group binds this
    # client" for a year because a byte-order mark stopped its parser opening a
    # group, and every path read as permitted. A renamed list here would empty
    # an instance's surface and report it fully maintained, so say so loudly.
    missing = {"GEOMETRY_URLS", "ROSTER_URLS"} - found
    if missing:
        fail("%s/sw.js: no %s list found. The surface would be silently short, "
             "and an instance with no files reads as fully maintained."
             % (tag, " or ".join(sorted(missing))))
    return out


# A FOLDER SERVED BY PREFIX IS ONE CLASS, NOT N FILES. `il/data/app/population/`
# holds 103 files — one per county plus an index — that `sw.js` serves by URL
# prefix rather than by listing, deliberately: precaching 6.6 MB for a feature
# most readers never open is the wrong trade, so the folder sits below the flat
# surface where `validate_index.py`'s one-list rule does not reach. Reading the
# sw.js lists alone would therefore drop all 103 without saying so, which is
# the defect above wearing a different hat. They enter as ONE row because they
# are one build, one gate and one clock: `scripts/build_block_population.py`
# writes every one of them from a single census vintage, so a plan that covers
# the folder covers each file and 103 rows would be 103 copies of one fact.
# THE KIND IS DECLARED HERE AND NOT READ, because no shape can be read off a
# folder, and the folder's clock is neither of the two the report already knows.
# Census 2020 block weights do not rot on reapportionment (the blocks are the
# census's, not a district plan's) and not on link rot; they are superseded by
# the next decennial census and by nothing else, which is a date rather than a
# cadence and so belongs on WATCH.md rather than in a weekly job.
PREFIX_CLASSES = {
    "il": [("il/data/app/population/", "census",
            "scripts/build_block_population.py")],
}
PREFIX_KIND = {rel: kind for rows in PREFIX_CLASSES.values()
               for rel, kind, _ in rows}


def prefix_classes(tag):
    out = []
    for rel, _kind, builder in PREFIX_CLASSES.get(tag, ()):
        d = os.path.join(REPO_ROOT, rel)
        if not os.path.isdir(d):
            fail("%s is recorded as a prefix-served class and is not in the "
                 "tree. Drop the entry or restore the folder." % rel)
        if not glob.glob(os.path.join(d, "*.json")):
            fail("%s holds no .json files; the class describes nothing." % rel)
        if not os.path.exists(os.path.join(REPO_ROOT, builder)):
            fail("%s names %s as its builder and that file is not in the tree."
                 % (rel, builder))
        out.append(rel)
    return out


# ---- the fourth test: COVERED --------------------------------------------
#
# Settled with Adam on 2026-10-01 and specified in `docs/DONE_STANDARD.md`,
# which is the rule of record; this is its implementation and takes its rules
# from that document. An app is Covered when it answers every level of
# government it is expected to answer, or carries a measured record of why it
# cannot.
#
# WHAT THIS SCORES IS WHETHER WE DID THE WORK, NOT WHETHER THE DATA EXISTS,
# which is the whole reason coverage was kept out of the standard in September
# and the reason it can be let back in now. A level no publisher offers, that we
# asked about and were refused, counts as covered; a level nobody has looked at
# does not. So a county clerk cannot fail an app — only we can.
#
# THE EXPECTED LIST IS ONE LIST FOR EVERY STATE and the entries are FUNCTIONS,
# not layer names: a county governing body is a board in Illinois and Wisconsin,
# supervisors in Iowa, commissioners in Michigan, a fiscal court in Kentucky, a
# legislature in New York. Each instance maps its own layers onto the function.
#
# WHY THE MAP IS DECLARED RATHER THAN DERIVED. Nothing in the tree says that a
# technical college district is a special district the state's law creates and a
# post office is not a government at all; no pattern over layer ids can tell
# them apart, and one that tried would be guessing in a report whose subject is
# honesty. So the map is stated, and two guards keep a stated map from rotting:
# every layer id it names must exist in that instance's own worksheet, so a
# rename fails the build; and every registered layer it does NOT name is printed
# on every run, so a layer that answers an expected function cannot sit
# unclaimed without somebody seeing it.
FUNCTIONS = (
    # number, key, title, required in every state
    (1, "us-house", "The U.S. House seat", True),
    (2, "state-legislature", "Both chambers of the state legislature", True),
    (3, "county-boundaries", "County boundaries", True),
    (4, "county-government",
     "The county governing body, in every county of the state", True),
    (5, "municipal-boundaries", "Municipal boundaries", True),
    (6, "local-government",
     "The governing body of every general-purpose local government "
     "above 25,000 people", True),
    (7, "school-district-boundaries", "School district boundaries", True),
    (8, "courts-by-district",
     "Courts whose judges are elected by district", False),
    (9, "sub-county-government",
     "Townships or other general-purpose sub-county governments", False),
    (10, "school-boards-by-district",
     "School boards elected by district", False),
    (11, "precincts", "Election precincts", False),
    (12, "special-districts",
     "Special districts the state's own law creates", False),
    (13, "tribal-government", "Tribal governments", False),
)

# Two entries have a SIZE in them rather than a layer, so they are measured
# against the state's own county list and against the committed population
# measurement rather than read off a map of layer ids.
class Entry(object):
    """How one instance stands on one expected function.

    `verdict` is one of:
      answered   the app answers it, and `layers` names what does
      depth      it has a size in it, so it is measured; `layers` names what
                 the app draws towards it, which the unclaimed-layer print needs
      open       nothing answers it yet — work to do, or a record to write
      unsettled  the standard leaves a question to that state's thread, and
                 nothing here measured it, so it is neither passed nor failed
                 quietly: it is printed as the question it is
      na         the function does not apply to this instance, reason stated
    """

    def __init__(self, verdict, layers=(), reason=None):
        self.verdict = verdict
        self.layers = tuple(layers)
        self.reason = reason


def answers(*layer_ids):
    return Entry("answered", layer_ids)


def depth(*layer_ids):
    return Entry("depth", layer_ids)


def na(reason):
    return Entry("na", reason=reason)


OPEN = Entry("open")
UNSETTLED = Entry("unsettled")


CITY_INSTANCE = ("San Francisco is one city, so its city tier is the whole app "
                 "and the state tiers above it are another app's subject.")

# A STATE WITH NO TRIBAL LAND IS THE STANDARD'S "the state does not have the
# level" CASE, and this reason is the record it asks for: the fact, and
# where it was checked. It was measured against the Census's own AIANNHA
# service — the current vintage's reservation, trust-land and state-reservation
# layers, resolved by `scripts/tribal_areas.py` — with a CONTROL whose answer
# was known before the query ran, because an ArcGIS service answers a bad query
# with HTTP 200 carrying an error envelope and a bare `.get("features", [])`
# turns that into a confident uniform zero.
#
# SAN FRANCISCO GETS NO GAP RECORD AND THAT IS DELIBERATE. A gap record tells a
# reader the app cannot answer something it should; here there is nothing on the
# ground to answer, so a record would be a false statement about the app rather
# than an honest absence. The fact belongs here, beside the test it settles.
NO_TRIBAL_LAND_SF = (
    "No tribal land lies inside San Francisco: measured 2026-10-01, the "
    "current-vintage reservation, trust-land and state-reservation layers "
    "return no feature intersecting the city's own shipped outline's extent, "
    "with a box over North Carolina's Qualla Boundary as the positive control.")

# Measured 2026-10-01 by this app's own thread; the working is in ca/WATCH.md.
SF_NO_COURT_DISTRICTS = (
    "No court-district line falls inside San Francisco. California elects its "
    "Supreme Court at large statewide, its Court of Appeal by appellate "
    "district, and — Cal. Const. art. VI sec. 16 — its superior court judges "
    "\"in their counties\". San Francisco is one consolidated city and county, "
    "and it sits whole inside the twelve-county First Appellate District, so "
    "both lines are the city's own edge.")

SF_SCHOOL_BOARDS_AT_LARGE = (
    "Neither San Francisco school board is elected by district. The San "
    "Francisco Unified School District's seven commissioners and City College "
    "of San Francisco's seven trustees are each elected by all of the "
    "district's voters, so there is no district to draw; the standard's "
    "at-large precedent is that naming the members is the whole answer, and "
    "both bodies are the city-wide school tier the app already covers.")

# Measured 2026-10-01 by Michigan's own thread; the working is in mi/WATCH.md.
MI_NO_SCHOOL_BOARD_DISTRICTS = (
    "Michigan elects no school board by district. Ordinary boards are elected "
    "at large under the Revised School Code; its one by-district scheme is for "
    "a first-class district, and no district is first-class; and the Detroit "
    "Public Schools Community District's board is elected districtwide under "
    "MCL 380.384(3). Every board contest on the Wayne and Macomb 2024 "
    "canvasses is districtwide.")

# Per instance, what answers each expected function. A tuple names the layer
# ids; `depth(...)` is measured; OPEN is nothing yet; UNSETTLED is a question the
# standard leaves to that state's thread.
ANSWERS = {
    "il": {
        "us-house": answers("congress"),
        "state-legislature": answers("il-senate", "il-house"),
        "county-boundaries": answers("county"),
        "county-government": depth("county-board"),
        "municipal-boundaries": answers("municipality"),
        "local-government": depth("ward"),
        "school-district-boundaries": answers("school-district-unified", "school-district-elementary", "school-district-secondary"),
        # Illinois elects its circuit judges from subcircuits in nine counties.
        "courts-by-district": answers("judicial-subcircuit"),
        # Illinois townships are limited purpose, which is why they are NOT in
        # the 25,000 city tier above; they are owed here, and the app draws them
        # and names Cook's township boards.
        "sub-county-government": answers("township"),
        "school-boards-by-district": answers("school-board"),
        "precincts": answers("county-precinct", "ward-precinct"),
        "special-districts": answers("fire-district", "park-district", "library-district", "mwrd", "ssa"),
        # SHIPPED 2026-10-01. Illinois holds exactly ONE governed tribal area —
        # the Prairie Band Potawatomi Nation's off-reservation trust land near
        # Shabbona — and the card names the NATION and the Kansas town it is
        # governed from, which is what this level asks for: a reader on that
        # ground is told which government answers for it. It names NO COUNCIL
        # MEMBER, and that is a narrower gap recorded as
        # `il-tribal-government` rather than a level unanswered: the nation's
        # own published list is the only authority for a council, and its site
        # answers this project with a Cloudflare managed challenge. The Census
        # draws no tribal subdivision on this land either, measured against a
        # positive control, so there is no district here for a seat to belong to.
        "tribal-government": answers("tribal-government"),
    },
    "wi": {
        "us-house": answers("us-house"),
        "state-legislature": answers("wi-senate", "wi-assembly"),
        "county-boundaries": answers("county"),
        "county-government": depth("county-board"),
        "municipal-boundaries": answers("municipality"),
        "local-government": depth("aldermanic-district"),
        "school-district-boundaries": answers("school-district-unified", "school-district-elementary", "school-district-secondary"),
        "courts-by-district": answers("wi-circuit-court", "wi-court-of-appeals"),
        # A Wisconsin town IS the general-purpose government outside a village
        # or city, and the app draws it — but what it names there is the town
        # CLERK, who does not govern. The standard's test is that a reader is
        # told who governs the point, so this is open rather than answered, and
        # `town-clerks-*.json` is named here as what was considered.
        "sub-county-government": OPEN,
        "school-boards-by-district": answers("mps-school-board"),
        "precincts": answers("ward"),
        "special-districts": answers("wtcs-district", "tid-district"),
        # SHIPPED 2026-10-01. The app draws all 21 pieces of tribal land in
        # Wisconsin -- 11 reservations and 10 of off-reservation trust land --
        # and names the nation that governs each and the town its government
        # sits in, which is what this level asks for: a reader on that ground
        # is told which government answers for it. It names NO COUNCIL MEMBER
        # for any of the 12 nations, and that is the narrower gap recorded as
        # `wi-tribal-government` rather than a level unanswered -- each
        # nation's own published list is the only authority for a council, and
        # the card states per nation which of the two reasons applies.
        "tribal-government": answers("tribal-government"),
    },
    "ia": {
        "us-house": answers("us-house"),
        "state-legislature": answers("ia-senate", "ia-house"),
        "county-boundaries": answers("county"),
        "county-government": depth("county-supervisor"),
        "municipal-boundaries": answers("municipality"),
        "local-government": depth("city-ward"),
        "school-district-boundaries": answers("school-district-unified"),
        "courts-by-district": answers("ia-judicial-district"),
        # Iowa townships are limited purpose and none reaches the city floor.
        # The app DRAWS them and, since 2026-10-01, names the clerk and trustees
        # of 186 of them from the twelve counties that publish a roster — which
        # is why the older reading here, that nothing draws a township
        # government, no longer describes the tree. It stays open on the
        # measurement rather than on that reading: Iowa has roughly 1,600 civil
        # townships, so about 1,400 still name nobody and the card says so on
        # every one of them.
        "sub-county-government": OPEN,
        "school-boards-by-district": answers("school-director-district"),
        "precincts": answers("precinct"),
        "special-districts": answers("community-college", "cc-director-district", "iowa-aea"),
        "tribal-government": OPEN,
    },
    "mi": {
        "us-house": answers("us-house"),
        "state-legislature": answers("mi-senate", "mi-house"),
        "county-boundaries": answers("county"),
        "county-government": depth("county-commissioner"),
        "municipal-boundaries": answers("municipality"),
        "local-government": depth("city-ward"),
        "school-district-boundaries": answers("school-district-unified", "school-district-elementary"),
        # Built 2026-10-01 from statute as unions of whole counties; the judges
        # are not named (gap mi-judge-roster: the court system's site refuses
        # every client).
        "courts-by-district": answers("mi-court-of-appeals", "mi-circuit-court"),
        # A Michigan township governs everyone outside a village or city, so
        # the 34 that clear 25,000 are already owed under the city tier; the
        # rest are owed here. The app draws all 1,240 and names the board of
        # each large township whose own page names every seat — the Illinois
        # precedent above, which answers this level by drawing every township
        # and naming Cook's 29 boards.
        "sub-county-government": answers("county-subdivision"),
        "school-boards-by-district": na(MI_NO_SCHOOL_BOARD_DISTRICTS),
        "precincts": answers("precinct"),
        # Intermediate school districts: special districts the Revised School
        # Code creates (MCL 380.601 et seq.), each with its own levy.
        "special-districts": answers("mi-isd"),
        # SHIPPED 2026-10-01, on the same builder and the same join as
        # Wisconsin's: 24 areas, 13 reservations and 11 of off-reservation
        # trust land, carrying 12 nations, each named with the town its
        # government sits in. The Ontonagon Reservation is the fleet's one
        # area the Census names and no BIA-listed government is filed under,
        # and it is answered from two measurements by one publisher rather
        # than inferred -- see `mi-tribal-government`, which is also where the
        # council absence is recorded, per nation.
        "tribal-government": answers("tribal-government"),
    },
    "mn": {
        "us-house": answers("us-house"),
        "state-legislature": answers("mn-senate", "mn-house"),
        "county-boundaries": answers("county"),
        # THE DISTRICTS SHIPPED 2026-10-01 AND THE LEVEL IS STILL OPEN, which is
        # the point of scoring this one by depth. Minn. Stat. 375.025 makes every
        # Minnesota county districted, so the app now draws all 447 commissioner
        # districts in all 87 counties — and the level asks for the governing
        # BODY, which means the people. No publisher pairs the 447 districts with
        # the people holding them, so no county is counted here yet
        # (gap mn-county-commissioner-roster, whose route is measured: five
        # county GIS layers carry the commissioner's name).
        "county-government": depth("county-commissioner"),
        "municipal-boundaries": answers("municipality"),
        "local-government": depth(),
        "school-district-boundaries": answers("school-district-unified", "school-district-elementary", "school-district-secondary"),
        # SETTLED 2026-10-01: Minn. Stat. 2.722 subd. 1 divides the state into
        # ten judicial districts by naming the counties in each, and Minnesota
        # elects its district court judges on a nonpartisan ballot within the
        # district they serve — so this is a district a reader votes in, and
        # the app draws all ten. It names no judge: www.mncourts.gov serves a
        # Cloudflare managed challenge to every client, which is an access
        # control (gap mn-judicial-roster).
        "courts-by-district": answers("mn-judicial-district"),
        "sub-county-government": OPEN,
        # SETTLED 2026-10-01 by this instance's own thread, and the answer is
        # that the level exists but only where a district has opted into it:
        # Minn. Stat. 205A.12 subds. 1-5 let a school district divide itself
        # into from three to seven election districts by board resolution or
        # by petition, and a district that has not done so elects its whole
        # board at large. So this is OPEN rather than the standard's "the
        # state does not have the level" case — and which districts have opted
        # in is not published anywhere this project has found, which is the
        # work the level is waiting on (mn/WATCH.md).
        "school-boards-by-district": OPEN,
        # The Secretary of State publishes all 4,105 precincts statewide, from
        # the office that maintains them, and the app draws them.
        "precincts": answers("voting-precinct"),
        # Watershed districts (Minn. Stat. ch. 103D) and the metro area's
        # watershed management organizations (103B.211), from the Board of
        # Water and Soil Resources' own statewide layer, 2026-10-06. Both can
        # levy a property tax, and the state's own law creates both — the
        # Wisconsin and Michigan precedent of one statewide family answering
        # this level. Not the only family Minnesota has: the Secretary of
        # State's precinct service also carries soil-and-water, hospital and
        # park districts, which are further layers rather than a gap here.
        "special-districts": answers("watershed-district"),
        "tribal-government": OPEN,
    },
    "ky": {
        "us-house": answers("us-house"),
        "state-legislature": answers("ky-senate", "ky-house"),
        "county-boundaries": answers("county"),
        "county-government": depth(),
        "municipal-boundaries": answers("municipality"),
        "local-government": depth(),
        # All three Census tilings, because Kentucky needs all three: measured
        # 2026-10-01, 170 unified districts plus 4 elementary ones partition the
        # state's land exactly (102,228.8 + 39.0 = 102,267.8 km2, which is the
        # 120-county total from the same service), and 4 secondary districts run
        # grades 9-12 over the same 39 km2. Shipping unified alone would answer
        # "no school district" to every reader inside those four areas.
        "school-district-boundaries": answers(
            "school-district-unified", "school-district-elementary",
            "school-district-secondary"),
        # ALL FOUR COURTS ANSWER, from statute text alone. Every Kentucky
        # judge is elected from a district or circuit made of WHOLE COUNTIES
        # named in the statute (KRS 21A.010, 22A.010(2), 23A.020, 24A.030), so
        # the three tilings dissolve offline from the county fabric this app
        # already ships — no publisher asked and no map read. Measured
        # 2026-10-01, each one partitions all 120 counties exactly once. Three
        # files answer four courts because KRS 22A.010(2) gives the Court of
        # Appeals the Supreme Court's own districts. Every unit's judges are
        # named since 2026-10-07 (Louisville's from the three Jefferson court
        # sites its Court of Justice page links), though the standard asks
        # whether the app answers the level and would count it without them.
        "courts-by-district": answers(
            "ky-supreme-court", "ky-court-of-appeals", "ky-circuit-court",
            "ky-district-court"),
        # KENTUCKY HAS NO SUB-COUNTY GENERAL-PURPOSE GOVERNMENT, which is the
        # standard's "the state does not have the level" case. Measured
        # 2026-10-01: the only sub-county units the Census publishes for
        # Kentucky are 493 Census County Divisions, which are statistical areas
        # drawn for tabulation and govern nobody, so there is no elected
        # sub-county body to draw. Recorded in ky/CLAUDE.md with the method.
        "sub-county-government": na(
            "Kentucky has no sub-county general-purpose government — outside a "
            "city limit the county governs. The 493 sub-county units the Census "
            "publishes for Kentucky are Census County Divisions: statistical "
            "areas, not governments."),
        # Kentucky owes these: its thread has confirmed every county school board
        # is elected by division, five per county from whole precincts, while its
        # independent school boards are elected at large and so are named rather
        # than drawn.
        "school-boards-by-district": OPEN,
        "precincts": OPEN,
        "special-districts": OPEN,
        # NO TRIBAL LAND IN KENTUCKY, measured 2026-10-01 against the Census
        # AIANNHA service over an envelope covering the whole state: zero
        # features in federal reservations, off-reservation trust lands, state
        # reservations, tribal subdivisions, and the state- and
        # tribal-designated statistical areas — six layers, all empty. RUN WITH
        # CONTROLS, because a zero from a query is also what an error looks
        # like: the same two layers return the Qualla Boundary over western
        # North Carolina and eleven reservations over northern Wisconsin. So
        # there is no tribal land here to draw, and this is the standard's
        # "the state does not have the level" case rather than work not done.
        # The fleet-wide tribal layer and its mandate stay the tribal thread's;
        # this entry only records Kentucky's own measurement.
        "tribal-government": na(
            "Kentucky has no tribal land. The Census publishes no federal or "
            "state reservation, no off-reservation trust land and no tribal "
            "statistical area anywhere in the state, measured 2026-10-01 with "
            "controls in North Carolina and Wisconsin."),
    },
    # Indiana, added at its 2026-10-07 go-live with the national tier only.
    # Every level it does not draw is OPEN rather than na: Indiana has every
    # one of them (two county bodies, 1,004 civil townships, elected school
    # boards, circuit courts by county, precincts, and one piece of Pokagon
    # trust land), and this app simply does not answer them yet.
    "in": {
        "us-house": answers("us-house"),
        "state-legislature": answers("in-senate", "in-house"),
        "county-boundaries": answers("county"),
        "county-government": depth(),
        "municipal-boundaries": answers("municipality"),
        "local-government": depth(),
        # UNIFIED ALONE TILES THE STATE: TIGERweb's elementary and secondary
        # school layers both answer zero features for STATE='18' (measured
        # 2026-09-29), so there is no second tiling to ship.
        "school-district-boundaries": answers("school-district-unified"),
        "courts-by-district": OPEN,
        "sub-county-government": OPEN,
        "school-boards-by-district": OPEN,
        "precincts": OPEN,
        "special-districts": OPEN,
        "tribal-government": OPEN,
    },
    "ny": {
        "us-house": answers("congress"),
        "state-legislature": answers("state-senate", "state-assembly"),
        "county-boundaries": answers("county", "borough"),
        # TWO LAYERS, ONE LEVEL, because New York's counties are governed in
        # two forms and the app answers both: a county that elects a legislature
        # from districts, and a county governed by a board of supervisors, where
        # the county board seat IS the town or city and the supervisor who runs
        # your town is the one who votes for you at the county. Measuring the
        # depth over both is what keeps the figure honest either way — a county
        # of either form counts once when it is answered and not at all when it
        # is not.
        "county-government": depth("county-legislature", "county-supervisor"),
        "municipal-boundaries": answers("municipality", "village"),
        "local-government": depth("council"),
        "school-district-boundaries": answers("nys-school-district", "nys-central-hs-district"),
        "courts-by-district": answers("judicial-district", "municipal-court"),
        # A New York town governs everyone outside a village or city, so the 67
        # that clear 25,000 are owed under the city tier; the rest are owed
        # here. The app draws towns and names no town board.
        "sub-county-government": OPEN,
        "school-boards-by-district": answers("cec"),
        "precincts": answers("election-district"),
        # Sullivan County's own register, the first county in this tier. New
        # York State's map server publishes not one statutory special district,
        # so this level is reached county by county; the twelve other layers in
        # Sullivan's service are tax-map assessment districts a town board
        # governs, with no body of their own, so they are not governments.
        "special-districts": answers("fire-district", "library-district"),
        "tribal-government": OPEN,
    },
    "ca": {
        "us-house": answers("congress"),
        "state-legislature": answers("ca-senate", "ca-assembly"),
        "county-boundaries": na(CITY_INSTANCE),
        # San Francisco's Board of Supervisors is both the county governing body
        # and the city council, drawn by district and named.
        "county-government": answers("supervisor-district"),
        "municipal-boundaries": na(CITY_INSTANCE),
        # Its city tier is one city, and the same board is its council,
        # drawn by district and named, so there is no size to measure.
        "local-government": answers("supervisor-district"),
        "school-district-boundaries": na(CITY_INSTANCE),
        # Both of these were left to this app's own thread and both are
        # settled now, measured 2026-10-01 and written up in ca/WATCH.md.
        # Neither is an absence anybody has to ask a publisher about: the
        # level does not exist inside this city, which is the standard's
        # "a state genuinely lacks a level" case.
        "courts-by-district": na(SF_NO_COURT_DISTRICTS),
        "sub-county-government": na(CITY_INSTANCE),
        "school-boards-by-district": na(SF_SCHOOL_BOARDS_AT_LARGE),
        "precincts": answers("election-precinct"),
        "special-districts": answers("bart-director"),
        "tribal-government": na(NO_TRIBAL_LAND_SF),
    },
}

# What names the governing body of each 25,000+ unit the app answers, and what
# the join is keyed on. A keyed roster is joined by the unit's own Census id; an
# instance that publishes one file per city declares the unit instead, because a
# filename is not a key.
#
# A city is answered when a reader clicking inside it is told who governs that
# point. Where the council elects by district that means the districts are drawn
# and the members named; where it elects at large, naming the members is the
# whole answer and there is no district to draw — which is why the test below is
# NAMES rather than districts. Many Illinois villages above the floor elect
# their trustees at large, and a rule demanding drawn districts would fail them
# for a boundary that does not exist.
CITY_ROSTERS = {
    # tag: (relative path, how the file's keys reach a Census place id)
    "il": [("il/data/app/municipal-officials.json", "geoid7")],
    # TWO FILES FOR WISCONSIN BECAUSE THE STATE ELECTS TWO WAYS. The first is
    # keyed by district; the second carries the municipalities that elect their
    # whole board at large, where there is no district to key on. Counting only
    # the first would read an at-large municipality as naming nobody, which is
    # the shape a first triage of this tier got wrong.
    "wi": [("wi/data/app/wi-alderpersons.json", "place5"),
           ("wi/data/app/wi-municipal-boards.json", "geoid7")],
    "ia": [("ia/data/app/ia-city-officials.json", "geoid7"),
           ("ia/data/app/ia-city-councils.json", "geoid7"),
           ("ia/data/app/ia-county-city-officials.json", "geoid7")],
    # Keyed by the Census id as written: 7 digits for a city, 10 for a
    # township (a county subdivision), which is the id the expected-units
    # measurement carries for each.
    "mi": [("mi/data/app/mi-municipal-officials.json", "geoid7")],
    # Election winners from the Secretary of State's city results files, keyed
    # by the city's Census id, each seat dated to the election that filled it.
    "mn": [("mn/data/app/mn-city-councils.json", "geoid7")],
}

# One file per city, so the unit is declared rather than keyed. A filename is
# not a key: `mi-grand-rapids-council-members.json` is a name somebody chose and
# the Census id is what the measurement carries, so the two are joined here once
# and the build fails if a declared id is not in the measurement.

CITY_FILES = {
    "ia": {"1912000": "ia/data/app/cedar-rapids-council-members.json",
           "1921000": "ia/data/app/dsm-council-members.json",
           "1982425": "ia/data/app/waterloo-council-members.json"},
    "mi": {"2605920": "mi/data/app/mi-battle-creek-commission-members.json",
           "2622000": "mi/data/app/mi-detroit-council-members.json",
           "2634000": "mi/data/app/mi-grand-rapids-council-members.json",
           "2641420": "mi/data/app/mi-jackson-council-members.json"},
    "ny": {"3651000": "ny/data/app/council-members.json"},
}


EXPECTED_GOVERNMENTS = os.path.join(REPO_ROOT, "docs", "expected-governments.json")


def worksheet_layer_ids(tag):
    """The layer ids this instance registers, from its own worksheet."""
    path = (os.path.join(REPO_ROOT, "metro-worksheet.json") if tag == "il"
            else os.path.join(REPO_ROOT, tag, "metro-worksheet.json"))
    with open(path, encoding="utf-8") as fh:
        return {l["id"] for l in json.load(fh)["layers"]}


def check_answer_map(live):
    """A stated map must keep describing the tree, in both directions.

    FORWARD: every layer id the map names must exist in that instance's own
    worksheet, so a rename fails the build rather than quietly un-answering an
    expected function. REVERSE: every registered layer the map does NOT name is
    printed, so a layer that answers an expected function cannot sit unclaimed
    without somebody seeing it. The reverse direction is a print and not a
    failure, because most layers are facilities and census geography rather than
    governments and no pattern can tell those apart.
    """
    missing = []
    for tag in live:
        if tag not in ANSWERS:
            fail("%s is live and has no entry in ANSWERS, so the fourth test "
                 "would skip it — and a skipped row reads like a passing one. "
                 "Map that instance's layers onto the expected functions in "
                 "scripts/build_eam_status.py." % tag)
        have = worksheet_layer_ids(tag)
        claimed = set()
        for key, entry in ANSWERS[tag].items():
            for lid in entry.layers:
                claimed.add(lid)
                if lid not in have:
                    missing.append("  %s: `%s` answers `%s` in the map and is "
                                   "not a layer this instance registers"
                                   % (tag, lid, key))
        for key in ANSWERS[tag]:
            if key not in {k for _, k, _, _ in FUNCTIONS}:
                fail("%s: ANSWERS names `%s`, which is not an expected "
                     "function. The list of functions is "
                     "docs/DONE_STANDARD.md's." % (tag, key))
        for _, key, _, _ in FUNCTIONS:
            if key not in ANSWERS[tag]:
                fail("%s: ANSWERS says nothing about the expected function "
                     "`%s`. Every entry gets a verdict, including `open`."
                     % (tag, key))
        unclaimed = sorted(have - claimed)
        print("build-eam-status: %s — %d of %d registered layer(s) answer an "
              "expected function; the rest are not claimed by one: %s"
              % (tag, len(claimed), len(have),
                 ", ".join(unclaimed) or "none"))
    if missing:
        fail("the expected-function map names layers that do not exist:\n"
             + "\n".join(missing))


def load_expected_units():
    """The committed 25,000+ measurement, audited before it is used.

    IT CANNOT GO STALE BEFORE 2030, which is why it is committed rather than
    re-fetched: the floor is a 2020 decennial count, so no unit crosses it until
    the next census. What CAN move is a unit's government — a village
    incorporating, a township charter — and that reaches this report through the
    rosters rather than through the population.
    """
    if not os.path.exists(EXPECTED_GOVERNMENTS):
        fail("docs/expected-governments.json is missing — run "
             "`python3 scripts/build_expected_governments.py` (it needs the "
             "network). The fourth test's city tier cannot be scored without "
             "it, and scoring it as covered would be a false pass.")
    with open(EXPECTED_GOVERNMENTS, encoding="utf-8") as fh:
        doc = json.load(fh)
    floor = doc.get("floor")
    if not isinstance(floor, int) or floor <= 0:
        fail("docs/expected-governments.json states no floor")
    seen = {}
    for tag, units in sorted(doc.get("units", {}).items()):
        if not units:
            fail("docs/expected-governments.json lists no unit for %s. A state "
                 "with no unit above the floor is possible, but it has never "
                 "been measured as empty here, so this is more likely a failed "
                 "fetch recorded as an answer." % tag)
        for u in units:
            if u["pop"] < floor:
                fail("docs/expected-governments.json: %s %s is below the "
                     "stated floor of %d" % (tag, u["geoid"], floor))
            if u["kind"] not in ("place", "subdivision"):
                fail("docs/expected-governments.json: %s %s has an unknown "
                     "kind %r" % (tag, u["geoid"], u["kind"]))
            if u["kind"] == "subdivision" and not doc.get(
                    "subdivision_is_general_purpose", {}).get(tag):
                fail("docs/expected-governments.json counts a county "
                     "subdivision in %s while recording that state's "
                     "subdivisions as not the general-purpose government. One "
                     "of the two is wrong." % tag)
            key = (tag, u["geoid"])
            if key in seen:
                fail("docs/expected-governments.json lists %s twice in %s"
                     % (u["geoid"], tag))
            seen[key] = u
    return doc


# The state each statewide app answers for, for the one join that needs it: a
# Wisconsin roster is keyed by the five-digit place code inside the state.
STATE_FIPS_OF = {"il": "17", "wi": "55", "ia": "19", "mi": "26",
                 "mn": "27", "ky": "21", "ny": "36", "in": "18"}


def _named_anywhere(record):
    """Does this unit's roster record name a person anywhere inside it?

    NESTED, through the report's own `_records` walk, because these rosters put
    the people a level or two down — Illinois under `board` and `head`, Wisconsin
    under `members` keyed by district, Iowa under `members`.

    THE UNIT RECORD'S OWN `name` IS THE UNIT'S NAME AND IS SKIPPED. Illinois
    writes "Village of Gurnee" there, and six of its units carry that and an
    office address and nobody at all; counting the top-level name would report
    each of them as a city whose government is named.

    AND THE TEST IS THE NAME'S SHAPE RATHER THAN `names_in`, which asks for a
    person field beside the name. That companion test is right where it is used —
    telling a person from a place in a file whose shape is unknown — and wrong
    here, where the file is a DECLARED roster of a governing body: Kenosha,
    Milwaukee, Racine, Sheboygan, Eau Claire and New Berlin publish their
    alderpersons as a bare name, so `names_in` answers nobody for all six and
    Wisconsin's city tier read 8 where it is 14. `is_name_shaped` is the fleet's
    one name-shape reader, which is what keeps this from being a second opinion
    about what a name is.
    """
    for sub in _records(record):
        if sub is not record:
            v = sub.get("name")
            if isinstance(v, str) and is_name_shaped(v):
                return True
        for key, _f, _w in ROLE_NAME_KEYS:
            v = sub.get(key)
            if isinstance(v, str) and is_name_shaped(v):
                return True
    return False


def city_tier(tag, expected):
    """Which of this state's 25,000+ units the app names a governing body for.

    The test is NAMES, because the standard's test is that a reader clicking
    inside the unit is told who governs that point: where the council elects at
    large there is no district to draw, and many units above the floor do.
    """
    units = {u["geoid"]: u for u in expected.get("units", {}).get(tag, [])}
    named = set()
    for rel, keyed_by in CITY_ROSTERS.get(tag, []):
        path = os.path.join(REPO_ROOT, rel)
        if not os.path.exists(path):
            fail("%s: the fourth test reads `%s` for its city tier and the "
                 "file is gone. Point CITY_ROSTERS at what replaced it rather "
                 "than letting the tier read as unanswered." % (tag, rel))
        with open(path, encoding="utf-8") as fh:
            roster = json.load(fh)
        if not isinstance(roster, dict):
            fail("%s: `%s` is not keyed by unit, so the city-tier join cannot "
                 "be made" % (tag, rel))
        hit = 0
        for key, record in roster.items():
            if keyed_by == "geoid7":
                geoid = str(key)
            elif keyed_by == "place5":
                geoid = STATE_FIPS_OF.get(tag, "") + str(key)
            else:
                fail("%s: CITY_ROSTERS asks for an unknown join `%s`"
                     % (tag, keyed_by))
            if geoid in units and _named_anywhere(record):
                named.add(geoid)
                hit += 1
        print("build-eam-status: %s — city tier: `%s` names a governing body "
              "for %d of this state's %d unit(s) at %s+"
              % (tag, rel, hit, len(units),
                 "{:,}".format(expected["floor"])))
    for geoid, rel in sorted(CITY_FILES.get(tag, {}).items()):
        path = os.path.join(REPO_ROOT, rel)
        if not os.path.exists(path):
            fail("%s: the fourth test reads `%s` for unit %s and the file is "
                 "gone" % (tag, rel, geoid))
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        if not _named_anywhere(doc):
            fail("%s: `%s` is declared as naming unit %s's governing body and "
                 "names nobody" % (tag, rel, geoid))
        if geoid not in units:
            fail("%s: CITY_FILES declares unit %s and the measurement does not "
                 "carry it. Either the unit has fallen below the floor or the "
                 "id is wrong; a declaration matching nothing is a pass nobody "
                 "earned." % (tag, geoid))
        named.add(geoid)
        print("build-eam-status: %s — city tier: `%s` names %s's governing body"
              % (tag, rel, units[geoid]["name"]))
    return units, named


# `_named_anywhere` decides whether a 25,000+ unit is answered, which is the
# whole of the fourth test's city tier, and both halves of it have been wrong
# once already in one sitting — too strict on six Wisconsin cities, too loose on
# six Illinois villages. So the cases are stated.
NAMED_UNIT_CASES = (
    ({"members": {"01": [{"name": "Eric J. Haugaard"}]}}, True,
     "Kenosha's shape: a bare name under a district, no person field beside it"),
    ({"board": [{"name": "Braden Meyer", "role": "Trustee"}],
      "head": {"name": "Tom Hundley", "role": "Mayor"}}, True,
     "Illinois's shape: people under `board` and `head`"),
    ({"members": [{"name": "Roy Miller", "role": "Mayor"}]}, True,
     "Iowa's shape: people under `members`"),
    ({"name": "Village of Gurnee", "county": "Lake",
      "office": {"address": "325 N O'Plaine Rd", "phone": "847-599-7500"},
      "url": "https://www.gurnee.il.us/"}, False,
     "the unit's own name and an address and nobody at all — six Illinois "
     "units look like this, and counting the top-level name would pass them"),
    ({"name": "City of Normal", "office": {"address": "11 Uptown Cir"}}, False,
     "the same, with no county"),
    ({"chair": "Jane Doe"}, True,
     "a declared role key at the top level is a person"),
    ({"districts": 4, "seats": 4, "municipality": "Altoona"}, False,
     "seat counts and a municipality name are structure, not people"),
)


# A ROSTER NOBODY ADDED TO THE TABLES ABOVE READS AS AN ABSENCE, SILENTLY. Both
# tables are stated, which is right -- a filename cannot say which unit a file
# names, and a clerk directory cannot say that a clerk does not govern -- but a
# stated table has one cost: a file nobody added reads exactly like a file that
# does not exist. On 2026-10-01 Iowa shipped its fourteen city councils and the
# city tier went on reporting 4 of 18 units answered, because the row that reads
# the file is written by hand and nobody wrote it. Nothing was red.
#
# So the sweep below runs the question backwards: any file in a live instance's
# own `data/app` whose keys reach units of that state at the floor AND which
# names people is a candidate for the city tier, and an undeclared candidate
# FAILS. Two ways to clear it -- read the file, or record here why it is not a
# governing body.
#
# Declared entries are re-audited every run and fail when they stop describing
# the tree, which is the property `ACCEPTED_DROPS` has: an entry naming a file
# that is gone, or one the sweep no longer finds, is an exception covering
# nothing.
CITY_ROSTER_NOT_GOVERNING = {
    # relative path: (why it is not a governing body, when that was decided)
    "wi/data/app/wi-municipal-clerks.json": (
        "A CLERK IS NOT A COUNCIL. This names the clerk of 608 Wisconsin "
        "municipalities, which is the person who runs the election and keeps "
        "the records, not the body that governs. Counting it would answer all "
        "35 of this state's units at the floor with nobody who holds a seat. "
        "Wisconsin's own instructions state this rule for exactly this file.",
        "2026-10-01"),
}


def city_roster_candidates(tag, expected):
    """Files in this instance's `data/app` that could answer its city tier.

    A candidate is keyed by the unit's own Census place id -- either the whole
    7-digit id or the 5-digit place within this state, the two joins the tables
    above use -- and names at least one person under a key that is a unit at the
    floor. Everything else in `data/app` is a different question: a 5-digit key
    is a county and a 10-digit one a county subdivision, and neither is the city
    tier.
    """
    units = {u["geoid"] for u in expected.get("units", {}).get(tag, [])}
    fips = STATE_FIPS_OF.get(tag, "")
    folder = os.path.join(REPO_ROOT, tag, "data", "app")
    found = {}
    if not units or not os.path.isdir(folder):
        return found
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".json"):
            continue
        rel = "%s/data/app/%s" % (tag, name)
        try:
            with open(os.path.join(folder, name), encoding="utf-8") as fh:
                doc = json.load(fh)
        except (ValueError, OSError):
            continue
        if not isinstance(doc, dict):
            continue
        hits = [k for k in doc
                if (str(k) in units or (fips and fips + str(k) in units))
                and isinstance(doc[k], (dict, list))
                and _named_anywhere(doc[k])]
        if hits:
            found[rel] = len(hits)
    return found


def check_city_rosters(live, expected):
    """Every candidate city roster is either read or recorded as not governing."""
    bad = 0
    read = {rel for rows in CITY_ROSTERS.values() for rel, _join in rows}
    read |= {rel for mapping in CITY_FILES.values()
             for rel in mapping.values()}
    seen = set()
    for tag in sorted(live):
        found = city_roster_candidates(tag, expected)
        for rel, hits in sorted(found.items()):
            seen.add(rel)
            if rel in read or rel in CITY_ROSTER_NOT_GOVERNING:
                continue
            bad += 1
            print("build-eam-status: FAIL — `%s` names people for %d of %s's "
                  "unit(s) at the floor and the city tier does not read it, so "
                  "those units read as unanswered. Either add it to "
                  "CITY_ROSTERS (or CITY_FILES, if it is one city) or record "
                  "in CITY_ROSTER_NOT_GOVERNING why it is not a governing "
                  "body." % (rel, hits, tag))
    for rel, (_why, when) in sorted(CITY_ROSTER_NOT_GOVERNING.items()):
        if not os.path.exists(os.path.join(REPO_ROOT, rel)):
            bad += 1
            print("build-eam-status: FAIL — CITY_ROSTER_NOT_GOVERNING records "
                  "`%s` (%s) and that file is gone, so the exception covers "
                  "nothing." % (rel, when))
        elif rel not in seen:
            bad += 1
            print("build-eam-status: FAIL — CITY_ROSTER_NOT_GOVERNING records "
                  "`%s` (%s) and the sweep no longer finds it, so the "
                  "exception covers nothing. Retire the entry." % (rel, when))
        else:
            print("build-eam-status: `%s` is recorded as not a governing body "
                  "(%s), still matching" % (rel, when))
    return bad


def check_named_unit():
    bad = 0
    for record, want, why in NAMED_UNIT_CASES:
        got = _named_anywhere(record)
        if got != want:
            bad += 1
            print("  UNIT  want=%s got=%s  (%s)" % (want, got, why))
    print("  UNIT  %d unit-roster case(s), %d named / %d not"
          % (len(NAMED_UNIT_CASES),
             sum(1 for _, w, _ in NAMED_UNIT_CASES if w),
             sum(1 for _, w, _ in NAMED_UNIT_CASES if not w)))
    return bad


def metro_key(tag):
    """The guidebook's own block name for this instance, read off its worksheet.

    `docs/DATA_LAYER_GUIDEBOOK.md` keys its gaps block by metro (`chicago`,
    `nyc`, `sf`) where this report keys by tag, and the mapping is in each
    instance's own `this_metro`. A hand table here would be a second copy of a
    fact the worksheets already carry, which is how `compose_app.SUBPAGES` came
    to miss five pages.
    """
    # ILLINOIS'S WORKSHEET IS AT THE REPO ROOT, NOT UNDER il/, and the first
    # version of this function looked only under <tag>/ — so metro_key("il")
    # returned None, blocks.get(None) returned None, and ALL 105 of Illinois's
    # gap records were dropped from the fourth test with nothing said. R2.3 kept
    # the repo-level files (metro-worksheet.json, metros.json, sitemap.xml) at
    # the root when the app moved into il/, which build_about_page.py and
    # audit_layer_provenance.py both already spell out the same way.
    ws = os.path.join(REPO_ROOT, *(("metro-worksheet.json",) if tag == "il"
                                   else (tag, "metro-worksheet.json")))
    # AND A MISSING WORKSHEET FAILS RATHER THAN RETURNING None. A None key reads
    # downstream as "this instance declares no records", which is exactly what a
    # state with a hundred records looks like when the path is wrong, and is the
    # silent-absence shape this report exists to refuse.
    if not os.path.exists(ws):
        fail("%s: no worksheet at %s, so the guidebook block holding this "
             "instance's gap records cannot be named. Every live instance has "
             "one; Illinois's is the repo-root file."
             % (tag, os.path.relpath(ws, REPO_ROOT)))
    with open(ws, encoding="utf-8") as f:
        key = json.load(f).get("this_metro")
    if not key:
        fail("%s: %s sets no `this_metro`, so there is no guidebook block name "
             "to read its gap records from"
             % (tag, os.path.relpath(ws, REPO_ROOT)))
    return key


ASK_CREDIT_CASES = (
    (None, False, "no ask at all — the ordinary state of a gap nobody has "
                  "written to, legal and worth nothing"),
    ({}, False, "an empty ask is the same as none"),
    ({"who": "County Clerk Amy Britton", "asked": "2026-08-01",
      "outcome": "refused"}, True,
     "a refusal counts straight away, with no follow-up needed"),
    ({"who": "County Clerk", "asked": "2026-06-01",
      "followedUp": "2026-06-22", "outcome": "unresponsive"}, True,
     "silence after one follow-up and thirty days"),
    ({"who": "County Clerk", "asked": "2026-06-01",
      "outcome": "answered"}, False,
     "an answered ask means the data is obtainable, so the work is to use it"),
    ({"who": "County Clerk", "asked": "2026-06-01"}, False,
     "an ask with no outcome has not reached one of the standard's two states"),
    ({"who": "County Clerk", "asked": "2026-06-01",
      "outcome": "pending"}, False,
     "a letter that is out and waiting earns nothing, whatever its date"),
    ({"who": "County Clerk", "asked": "2026-01-01",
      "followedUp": "2026-01-20", "outcome": "pending"}, False,
     "and still nothing once the thirty days are long past: only the thread "
     "writing `unresponsive` moves it, never the calendar"),
)


def check_ask_credit():
    bad = 0
    for ask, want, why in ASK_CREDIT_CASES:
        got, _note = ask_credit(ask)
        if got != want:
            bad += 1
            print("  ASK   want=%s got=%s  (%s)" % (want, got, why))
    print("  ASK   %d ask-credit case(s), %d credited / %d not"
          % (len(ASK_CREDIT_CASES),
             sum(1 for _, w, _ in ASK_CREDIT_CASES if w),
             sum(1 for _, w, _ in ASK_CREDIT_CASES if not w)))
    return bad


def ask_credit(ask):
    """(qualifies, note) for one record's `ask` block.

    The standard's rule, and nothing more: a refusal counts straight away,
    silence counts once we have asked, followed up once and waited thirty days
    from that follow-up. Anything else earns nothing and says why.

    THE THIRTY DAYS ARE NOT COUNTED HERE. `build_coverage_gaps.ask_problems`
    refuses an `unresponsive` claim whose own follow-up date is more recent than
    that, in CI, so the outcome this function reads is one the dates already
    bear out. Counting them again would put the verdict on the calendar: the
    same record would earn nothing one morning and credit the next with nothing
    edited, which moves a generated document by the clock and fails `--check` on
    a day nobody touched the tree.
    """
    if not ask:
        return False, ("no ask recorded, so it covers nothing yet under the "
                       "standard")
    outcome = ask.get("outcome")
    if outcome == "refused":
        return True, "%s refused on %s" % (ask.get("who"), ask.get("asked"))
    if outcome == "unresponsive":
        return True, ("%s asked %s, followed up %s, no reply in %d days"
                      % (ask.get("who"), ask.get("asked"),
                         ask.get("followedUp"), ASK_SILENCE_DAYS))
    if outcome == "answered":
        return False, ("the ask was answered, so this level is work to do "
                       "rather than a level to record")
    if outcome == "pending":
        # SENT AND WAITING, WHICH IS NOT ONE OF THE STANDARD'S TWO STATES. It
        # earns nothing however old it is, and deliberately says so without
        # arithmetic: reading the clock here would flip this record the morning
        # the thirtieth day passed, with nothing edited. The clock is printed by
        # `build_coverage_gaps.pending_ask_lines`, on stdout, where no committed
        # byte depends on it.
        return False, ("%s was asked on %s and has not answered; the record "
                       "earns nothing until a thread writes the outcome"
                       % (ask.get("who"), ask.get("asked")))
    return False, "ask outcome %r earns nothing" % outcome


def covering_records(live):
    """{tag: {function key: [record]}} — every gap record declaring `covers`.

    Each record is (id, qualifies, note, unit). `unit` is the id after the colon
    in a `<level key>:<unit id>` entry, or None for a claim about a whole level.
    A level measured over every county or every large town is credited UNIT BY
    UNIT, so it needs the unit; `score_covered` refuses a whole-level claim on
    one of those by name.

    `qualifies` is the standard's own rule
    in `docs/DONE_STANDARD.md`: a refusal counts straight away, silence counts
    once we have asked, followed up once and waited thirty days from the
    follow-up. A record with no `ask` is legal and qualifies for nothing, which
    the standard asks be SAID rather than passed — so it is returned with its
    reason and printed, not dropped.

    THE DATES ARE NOT RE-ARITHMETICKED HERE. `build_coverage_gaps.ask_problems`
    already refuses an `unresponsive` claim its own follow-up date does not
    support, in CI, so by the time a record reaches this function the outcome it
    states is one the dates bear out. Two readers of the thirty days is exactly
    the duplication this repository keeps finding wrong; this one reads the
    stated outcome and names the gate that holds it.

    A `covers` key no function uses FAILS, by name: the whole point of the field
    is to join a record to a level, and a typo joins it to nothing while looking
    exactly like a record that counts.
    """
    known = {key for _n, key, _t, _r in FUNCTIONS}
    blocks = load_gaps()
    out = {}
    for tag in live:
        key = metro_key(tag)
        per = {}
        for rec in blocks.get(key) or []:
            covers = rec.get(COVERS)
            if not covers:
                continue
            gid = rec.get("id") or "<unnamed record>"
            claims = []
            for entry in covers:
                fkey, _sep, unit = entry.partition(":")
                unit = unit.strip() or None
                if fkey not in known:
                    fail("%s: gap record `%s` says it covers %r and no expected "
                         "level has that key. The keys are the ones in "
                         "`FUNCTIONS`: %s"
                         % (tag, gid, fkey, ", ".join(sorted(known))))
                claims.append((fkey, unit))
            qualifies, note = ask_credit(rec.get(ASK))
            for fkey, unit in claims:
                per.setdefault(fkey, []).append((gid, qualifies, note, unit))
        out[tag] = per
    return out


def _names_a_body(rec):
    """Does this county record name anybody on its governing body?

    Two shapes, because the fleet's boards come in two: a districted board
    keys its people under `districts[].members[]`, and a board elected AT
    LARGE has no districts at all and carries `members[]` at the top of the
    record beside `at_large`. Both are a county naming its governing body.
    """
    for d in rec.get("districts") or []:
        for m in d.get("members") or []:
            if isinstance(m, dict) and m.get("name"):
                return True
    for m in rec.get("members") or []:
        if isinstance(m, dict) and m.get("name"):
            return True
    return False


def score_covered(tag, counties_named, total_counties, expected, records,
                  named_counties=()):
    """Every expected function for one instance: verdict, and why.

    Returns (entries, covered) where `entries` is one record per function in the
    standard's own order and `covered` is True only when every function is
    answered or does not apply. An `open` or `unsettled` function fails, and the
    two are reported differently: open is work to do or a record to write,
    unsettled is a question the standard hands to that state's thread.

    A RECORD CAN NOW COVER A FUNCTION, which is what `covers` and `ask` on a
    gap record are for. The standard lets a written record stand in for a level
    the app cannot answer, but only after a dated ask: a refusal counts at once,
    silence once we have asked, followed up and waited thirty days. A qualifying
    record turns `open` into `recorded`, which satisfies the test.

    A record that declares `covers` and carries no qualifying ask leaves the
    function OPEN and is reported beside it with the reason. That is the
    standard's own instruction — "a record written without an ask does not
    count, and the report should say so rather than pass it" — and it is the
    direction that matters, because the cheap failure here is an app passing on
    a note somebody wrote without ever contacting a publisher.

    A record is never credited against a function the app ALREADY answers: the
    verdict is read before the records are, so a stray `covers` cannot turn a
    real answer into a recorded one.
    """
    entries = []
    for number, key, title, required in FUNCTIONS:
        entry = ANSWERS[tag][key]
        verdict, detail = entry.verdict, None
        # `short_units` is None where the level is NOT measured unit by unit,
        # and otherwise the ids of the units the app does not answer. Its
        # presence is what makes a level credited per unit below.
        short_units, unit_universe = None, None
        unit_word = unit_plural = None
        if verdict == "depth":
            if key == "county-government":
                if total_counties is None:
                    verdict = "na"
                    detail = NO_COUNTY_TIER.get(tag)
                else:
                    short = total_counties - counties_named
                    verdict = "answered" if short == 0 else "open"
                    detail = ("%d of %d counties name a governing body"
                              % (counties_named, total_counties))
                    # THE COUNTY UNIVERSE IS A COUNT, NOT A LIST. STATE_COUNTIES
                    # holds a number on purpose (every derivable list is a
                    # coverage list, which would make the denominator vacuous),
                    # so the unanswered counties cannot be enumerated and a
                    # credited slug cannot be checked against a universe. What
                    # CAN be checked is the arithmetic: the level closes only
                    # when the counties that name a body plus the distinct
                    # counties with a credited record reach the state's total,
                    # and a slug naming an already-answered county earns
                    # nothing. So `short_units` is the shortfall as a NUMBER of
                    # unnamed counties, carried as an opaque sentinel rather
                    # than a set.
                    short_units = short
                    unit_word, unit_plural = "county", "counties"
                    unit_universe = set(named_counties)
            elif key == "local-government":
                units, named = city_tier(tag, expected)
                short = len(units) - len(named)
                verdict = "answered" if short == 0 else "open"
                detail = ("%d of %d units at %s+ name a governing body"
                          % (len(named), len(units),
                             "{:,}".format(expected["floor"])))
                if short:
                    rest = sorted((u["name"] for g, u in units.items()
                                   if g not in named))
                    detail += "; unanswered: " + ", ".join(rest[:8])
                    if len(rest) > 8:
                        detail += " and %d more" % (len(rest) - 8)
                short_units = {g for g in units if g not in named}
                unit_universe = set(units)
                unit_word, unit_plural = "unit", "units"
            else:
                fail("%s: `%s` is measured as a depth entry and nothing "
                     "measures it" % (tag, key))
        elif verdict == "answered":
            detail = ", ".join("`%s`" % l for l in entry.layers)
        elif verdict == "na":
            detail = entry.reason
        claimed = records.get(key) or []
        # ONE LETTER MUST NOT PASS A WHOLE TIER. A level measured over every
        # county or every large town used to turn `recorded` the moment ANY
        # record covering it qualified, so one city's refusal would have passed
        # a state's whole local tier with the other units unasked. A record on
        # such a level therefore names the unit it is about, and the level
        # closes only when EVERY unanswered unit has one.
        if short_units is not None:
            # A WHOLE-LEVEL CLAIM WITH NO QUALIFYING ASK IS LEGAL AND EARNS
            # NOTHING, which is the ordinary state of a level nobody has written
            # to yet — New York's two are exactly that, and a first version of
            # this refused them on SHAPE alone, failing the build over records
            # that could never have been credited. The fault Michigan found is
            # about CREDITING, so that is where the refusal belongs: a claim
            # carrying an ask that counts must name its units, because that is
            # the one that would otherwise pass a tier on one letter.
            for gid, qualifies, _n, unit in claimed:
                if unit is None and qualifies:
                    fail("%s: gap record `%s` carries an ask that counts and "
                         "claims the whole of `%s`, which is measured %s by %s. "
                         "Name the %s it is about, as `%s:<%s id>` — one letter "
                         "cannot speak for the %s nobody has asked about."
                         % (tag, gid, key, unit_word, unit_word, unit_word,
                            key, unit_word, unit_plural))
        else:
            for gid, _q, _n, unit in claimed:
                if unit is not None:
                    fail("%s: gap record `%s` names unit %r under `%s`, which "
                         "is answered for the whole state at once rather than "
                         "unit by unit. Drop the unit."
                         % (tag, gid, unit, key))

        credited = [r for r in claimed if r[1]]
        if verdict == "open" and short_units is not None:
            # A credited unit the app already answers earns nothing and is
            # reported: it is a record written about the wrong unit, which is a
            # mistake worth seeing rather than a free pass.
            answered_already = sorted(
                {u for _g, q, _n, u in credited
                 if q and unit_universe is not None and u in unit_universe})
            got = {u for _g, q, _n, u in credited
                   if q and not (unit_universe is not None
                                 and u in unit_universe)}
            if isinstance(short_units, set):
                outside = sorted(got - short_units)
                if outside:
                    fail("%s: `%s` has credited record(s) naming %s, which is "
                         "not a unit this level measures. The level's units are "
                         "this state's %s at the standard's floor."
                         % (tag, key, ", ".join(repr(u) for u in outside),
                            unit_plural))
                left = len(short_units - got)
                closed = len(short_units) - left
                total_short = len(short_units)
            else:
                left = max(short_units - len(got), 0)
                closed, total_short = len(got), short_units
            if closed:
                detail = ((detail.rstrip(". ") + ". " if detail else "")
                          + "%d of the %d unanswered %s %s a credited "
                            "record: %s"
                          % (closed, total_short, unit_plural,
                             "has" if closed == 1 else "have",
                             "; ".join("`%s` (%s) — %s" % (gid, u, note)
                                       for gid, q, note, u in credited if q)))
            if closed and left == 0:
                verdict = "recorded"
            elif closed and left:
                # Only where there is PARTIAL credit. With no credited record
                # the first clause already says how many units are unanswered,
                # and repeating it would make every open level carry the same
                # number twice.
                detail = ((detail.rstrip(". ") + ". " if detail else "")
                          + "The other %d still %s neither an answer nor a "
                            "credited record, so the level stays open"
                          % (left, "has" if left == 1 else "have"))
            if answered_already:
                detail = ((detail.rstrip(". ") + ". " if detail else "")
                          + "Credited record(s) name %s, which the app already "
                            "answers, so they earn nothing here"
                          % ", ".join(answered_already))
        elif verdict == "open" and credited:
            verdict = "recorded"
            detail = "; ".join("`%s` — %s" % (gid, note)
                               for gid, _q, note, _u in credited)
        # A whole-level claim on a per-unit level cannot be credited, so it is
        # never in `credited` and falls through to the earns-nothing line below
        # with its own reason.
        if verdict == "open" and claimed and not credited:
            unearned = "; ".join(
                "`%s`%s — %s" % (gid, " (%s)" % u if u else "", note)
                for gid, _q, note, u in claimed)
            detail = ((detail.rstrip(". ") + ". " if detail else "")
                      + "A record declares this level and earns nothing: "
                      + unearned)
        entries.append(dict(number=number, key=key, title=title,
                           required=required, verdict=verdict, detail=detail,
                           layers=entry.layers, claimed=claimed))
    covered = all(e["verdict"] in ("answered", "na", "recorded")
                  for e in entries)
    return entries, covered


# THE FOURTH TEST USED TO SCORE NEW YORK'S COUNTY TIER WHILE E AND A DASHED IT,
# on the reading recorded above, and that divergence is gone: New York is scored
# statewide on all four tests, so this table is STATE_COUNTIES and the keys
# agree by construction. It is kept as its own name because the two questions
# are still different ones — E asks where we looked and C asks what we ship — and
# a state could again need a different denominator for the two. San Francisco
# has no county above it to ship, so its entry is absent and reads as "does not
# apply" rather than as a failing zero.
COVERED_COUNTIES = dict(STATE_COUNTIES)


def measure(counties, paths, B):
    staged = staged_paths()
    watchers = watcher_texts()
    live = live_instances()
    check_county_universe(live)
    check_answer_map(live)
    expected = load_expected_units()
    if check_city_rosters(live, expected):
        sys.exit(1)
    covering = covering_records(live)
    rows = []

    for tag in live:
        scored = tag not in NO_COUNTY_TIER
        total = STATE_COUNTIES.get(tag)
        ring = ring_size(tag)
        if scored:
            if ring is None:
                fail("%s: no METRO_COUNTY_FIPS in %s — the county universe cannot "
                     "be checked" % (tag, os.path.relpath(outline_path(tag), REPO_ROOT)))
            if ring > total:
                fail("%s: the coverage ring holds %d counties and STATE_COUNTIES "
                     "says the state has %d. One of the two is wrong, and E's "
                     "denominator depends on it." % (tag, ring, total))

        served = {B.slug_of(name) for name in counties.get(tag, {})}
        recorded, statewide = gap_counties(tag)
        covered = served | recorded
        # A STATEWIDE RECORD COVERS THE REST, AND BOTH NUMBERS ARE KEPT. The
        # per-county figure is what a state's own research looks like, so it is
        # carried beside the statewide one rather than replaced by it — reporting
        # 99/99 on the strength of one declaration would hide the fact that Iowa
        # got there county by county and did not need the declaration at all.
        short = (total - len(covered)) if scored else 0
        # LOAD-BEARING ONLY WHERE IT CHANGES THE ANSWER. Iowa and Michigan both
        # publish a record covering every county and both already reach their
        # whole state one county at a time, so saying "Examined does not rest on
        # county-by-county records here" would be false of them — it is true of
        # Minnesota and Kentucky, which reach 0 of 87 and 0 of 120 that way. The
        # console line below names every such record on every run whether or not
        # it carries weight, so one cannot go unseen.
        load_bearing = sorted(statewide) if (scored and short > 0) else []
        unexamined = 0 if load_bearing else short
        if statewide:
            print("build-eam-status: %s — %d statewide gap record(s) covering "
                  "every county: %s%s"
                  % (tag, len(statewide), ", ".join(sorted(statewide)),
                     "" if load_bearing else
                     " (not load-bearing — the state already reaches "
                     "%d of %d counties one at a time)"
                     % (len(covered), total) if scored else ""))

        districts = unanswered = people = 0
        unanswered_names = []
        # The SLUGS of the counties that name a governing body, not just how
        # many: the fourth test credits a county-level record by the county it
        # names, and a record naming a county the app already answers has to be
        # told apart from one naming a county nobody has reached.
        named_counties = set()
        for name, rec in counties.get(tag, {}).items():
            # A COUNTY NAMES A GOVERNING BODY WHEN ANY OF ITS SEATS NAMES
            # SOMEBODY, which is the fourth test's county-tier question and is
            # not the same as Answered's: Answered asks whether every district
            # the app DRAWS says something, and passes a county whose board is
            # recorded as unavailable. Covered asks how many of the state's
            # counties the app answers at all.
            #
            # AN AT-LARGE BOARD HAS NO DISTRICTS AND ITS MEMBERS SIT AT THE TOP
            # OF THE RECORD, so a walk of `districts` alone finds nothing in it
            # and the county reads as naming nobody. Measured on 2026-10-01, 20
            # Illinois and 70 Iowa records are that shape and every one names
            # real people, so Illinois published 63 of 102 counties where it is
            # 83 and Iowa 21 of 99 where it is 91. The standard is explicit that
            # naming the members IS the whole answer for a body elected at
            # large — there is no district to draw — so both shapes count.
            # Wisconsin and Michigan carry no flat records and do not move.
            #
            # The two routes are exhaustive on today's tree: 63 + 20 = 83 is
            # every Illinois county with a record and 21 + 70 = 91 every Iowa
            # one, so no county is left naming somebody by a third route.
            if _names_a_body(rec):
                named_counties.add(B.slug_of(name))
            for d in rec.get("districts") or []:
                districts += 1
                people += sum(1 for m in d.get("members") or []
                              if (m.get("name") or "").strip())
                if not d.get("members") and not d.get("vacancies") and not d.get("note"):
                    unanswered += 1
                    if len(unanswered_names) < 12:
                        unanswered_names.append("%s district %s" % (name, d.get("label")))

        # HOW ANSWERED WAS EARNED, because "all" over a county tier that draws
        # nothing yet is a stronger sentence than the tree supports. The standard
        # gives a district three ways to pass — a name, a vacancy the county
        # states, or a note saying why no name can be shown — and an instance
        # whose county districts are not on the map yet passes on the third,
        # through the records that say so. That is a weaker guarantee than a
        # named seat, exactly as a watched file is weaker than a rewritten one,
        # so the report says which.
        if districts:
            answered_by = "name"
        elif recorded or statewide:
            answered_by = "record"
        else:
            answered_by = None

        # THE SURFACE IS EVERY DATA FILE THE APP READS, not the roster files
        # alone. Wisconsin found that hole: M flagged a 72-record directory of
        # seat counts and missed county-supervisory-districts.json, the 1,590
        # districts it is derived from and the file the whole county-board card
        # is drawn on. A bar that fails the restatement and passes the source
        # is not measuring what it claims to.
        surface = sorted(
            {os.path.relpath(p, REPO_ROOT) for p in set(paths.get(tag, ()))} |
            set(app_data_files(tag)) | set(prefix_classes(tag)))

        planned_rows, class_globs = watch_rows(tag)
        # THE CEILING COUNTS WHAT A PATTERN COULD MATCH, NEVER WHAT IT WAS LEFT,
        # and the first version counted the leftovers — which made it nearly
        # vacuous, caught by its own negative test. The lookup below breaks on
        # the FIRST matching row, so a blanket `*-districts.json` written under
        # the narrow rows only ever claimed the files they had not taken, and a
        # guard reading those claims would have passed it. Counted against the
        # whole surface instead, a blanket is a blanket wherever it sits.
        glob_reach = {label: sum(1 for r in surface
                                 if rx.match(os.path.basename(r) or r))
                      for rx, label, _ in class_globs}
        glob_hits = {label: 0 for _, label, _ in class_globs}
        unmaintained, watched, planned = [], [], []
        for rel in surface:
            if refreshed_by(rel, staged):
                continue
            hits = watched_by(rel, watchers)
            if hits:
                watched.append((rel, hits[0]))
                continue
            # A folder class is keyed by its own path; `os.path.basename` of a
            # path ending in "/" is the empty string, which would look up
            # nothing and read as unplanned forever.
            base = rel if rel.endswith("/") else os.path.basename(rel)
            when = planned_rows.get(base)
            if not when:
                for rx, label, cadence in class_globs:
                    if rx.match(base):
                        when, glob_hits[label] = cadence, glob_hits[label] + 1
                        break
            if when:
                planned.append((rel, when))
                continue
            # What the unrefreshed file IS, which is what decides how fast it
            # rots. Read off the file's own shape rather than the adapter's
            # output: a directory of seat counts contributes no districts, so
            # the adapter view cannot tell it from an empty one.
            unmaintained.append((rel,) + shape_of(os.path.join(REPO_ROOT, rel)))

        for label, reach in sorted(glob_reach.items()):
            claimed = glob_hits[label]
            print("build-eam-status: %s — WATCH.md class `%s` matches %d file(s)"
                  "%s" % (tag, label, reach,
                          "" if claimed == reach
                          else ", %d of them claimed here (the rest by an "
                               "earlier row)" % claimed))
            # A THIRD OF A SEVEN-FILE INSTANCE IS TWO, which refuses a row
            # naming three files of one kind and is not what this guard is for.
            # Its subject is a BLANKET — one cadence claimed over so much of an
            # instance that it must be covering several different clocks, which
            # fire, park, library and board districts do not share. At Illinois's
            # 398 files a third is 132 and the ceiling bites where it should; at
            # Minnesota's 7 it bites on an honest class row. Raised by the Iowa
            # thread, which hit it at Iowa's size. So the ceiling is a third or
            # four files, whichever is larger: four is stated rather than derived,
            # and it is the smallest number at which a class row can name more
            # than a pair without being called a blanket.
            ceiling = max(len(surface) // 3, 4)
            if reach > ceiling:
                fail("%s: WATCH.md class `%s` matches %d of %d files on the "
                     "surface, past this instance's ceiling of %d. One cadence "
                     "over that much of an instance is a claim about several "
                     "different clocks; split the row."
                     % (tag, label, reach, len(surface), ceiling))

        counties_named = len(named_counties)
        cov_entries, cov = score_covered(
            tag, counties_named, COVERED_COUNTIES.get(tag), expected,
            covering.get(tag) or {}, named_counties)

        rows.append(dict(
            tag=tag, scored=scored, total=total, ring=ring,
            served=len(served), recorded=len(recorded), covered=len(covered),
            statewide=statewide, load_bearing=load_bearing,
            unexamined=unexamined,
            districts=districts, people=people, answered_by=answered_by,
            unanswered=unanswered, unanswered_names=unanswered_names,
            rosters=len(surface), unmaintained=unmaintained,
            watched=watched, planned=planned,
            # None, never False, where a test does not apply to this instance.
            # A city instance has no county frontier, and scoring it zero would
            # read as a failing state rather than as the wrong question.
            E=(unexamined == 0) if scored else None,
            A=(unanswered == 0 and answered_by is not None) if scored else None,
            M=(not unmaintained),
            counties_named=counties_named,
            covered_entries=cov_entries,
            C=cov,
        ))
    return rows


TESTS = ("E", "A", "M", "C")


def letters(row):
    """E.A.M.C. for this row, with `-` where a test does not apply.

    A dot is a test this instance failed and a dash is one it was never asked,
    and the two must not render alike: `··M·` for San Francisco would read as an
    instance failing three bars when it is answering the ones it has.
    """
    return "".join("-" if row[L] is None else (L if row[L] else "\u00b7")
                   for L in TESTS)


def is_done(row):
    """Done when every test that APPLIES is met."""
    return all(row[L] is not False for L in TESTS)


VERDICT_WORD = {"answered": "answered", "open": "open",
                "recorded": "covered by a record", "unsettled": "unsettled",
                "na": "does not apply"}


def covered_lines(row):
    """The fourth test for one instance, level by level, in the standard's order.

    A level covered by a RECORD is printed as well as a level that is short.
    Passing on a written record is a different thing from answering, and the
    whole point of the fourth test is that the difference stays legible — a
    credited level dropping silently out of this list would make an app read as
    though it answered something it only accounted for.

    THE FLOOR SENTENCE IS CONDITIONAL, because it is a claim about this
    instance and it stops being true the moment one of its records is credited.
    A first draft stated it unconditionally; it was correct on the day the test
    shipped, when nothing declared `covers`, and would have gone on telling a
    reader that nothing is credited underneath a list of credited levels.
    """
    out = []
    entries = row["covered_entries"]
    short = [e for e in entries if e["verdict"] not in ("answered", "na",
                                                       "recorded")]
    recorded = [e for e in entries if e["verdict"] == "recorded"]
    unearned = [e for e in short if e.get("claimed")]
    if not short:
        out.append("- **Covered: yes.** Every expected level of government is "
                   "answered%s."
                   % ("" if not recorded else
                      " or covered by a record, %d of them by record"
                      % len(recorded)))
        for e in recorded:
            out.append("  - **%d. %s** — covered by a record rather than "
                       "answered: %s"
                       % (e["number"], e["title"], e["detail"]))
        _append_not_applicable(row, out)
        return out
    floor = ("Each is a floor: a level listed here may already have a "
             "record behind it that does not yet say which level it "
             "covers." if not unearned else
             "A level whose record earns nothing says so underneath it.")
    out.append("- **Covered: no.** %d of the %d expected levels of "
               "government are not answered. %s"
               % (len(short), len(entries), floor))
    for e in short:
        out.append("  - **%d. %s** — %s%s%s"
                   % (e["number"], e["title"], VERDICT_WORD[e["verdict"]],
                      "" if e["required"] else " (required only where the "
                                               "state has the level)",
                      (". " + e["detail"]) if e["detail"] else ""))
        if e["verdict"] == "unsettled":
            out.append("    The standard leaves this one to this app's own "
                       "thread: whether the level exists here at all has not "
                       "been measured, so it is neither passed nor failed "
                       "quietly.")
    for e in recorded:
        out.append("  - **%d. %s** — covered by a record rather than answered: "
                   "%s" % (e["number"], e["title"], e["detail"]))
    _append_not_applicable(row, out)
    return out


def _append_not_applicable(row, out):
    """List the levels that do not apply here, with the reason each time.

    A LEVEL THAT DOES NOT APPLY USED TO RENDER NOWHERE, which is the shape this
    project keeps finding wrong: the test passes and a reader of the report
    cannot see on what grounds. The standard's own words for this branch are
    that "the record states the fact and where it was checked", so the fact and
    the check are printed rather than left in this file's source.
    """
    skipped = [e for e in row["covered_entries"] if e["verdict"] == "na"]
    if not skipped:
        return
    out.append("- **Does not apply here (%d):** each one below is counted "
               "towards Covered by a stated fact rather than by work."
               % len(skipped))
    for e in skipped:
        out.append("  - **%d. %s** — %s" % (e["number"], e["title"],
                                            e["detail"] or "reason not stated"))


def render(rows):
    out = []
    out.append("# E.A.M.C. status")
    out.append("")
    out.append("**Generated by `scripts/build_eam_status.py` — never hand-edit.**")
    out.append("`--check` runs in CI. Regenerate after any roster, gap-record or")
    out.append("workflow change.")
    out.append("")
    out.append("A state is **done** when it is Examined, Answered, Maintained")
    out.append("and Covered, at which point its session moves from expansion to")
    out.append("maintenance. The mark is computed on every run and **goes")
    out.append("backward** the moment a tranche lands without records, a district")
    out.append("stops naming anyone, a roster loses its scheduled job, or a layer")
    out.append("that answered an expected level stops shipping.")
    out.append("")
    out.append("**Covered** is the fourth test, settled on 2026-10-01 and specified")
    out.append("in [`DONE_STANDARD.md`](DONE_STANDARD.md): the app answers every")
    out.append("level of government it is expected to answer, or carries a measured")
    out.append("record of why it cannot. It scores **whether we did the work, not")
    out.append("whether the data exists** — a level no publisher offers, that we")
    out.append("asked about and were refused, counts as covered — so a county")
    out.append("publisher cannot fail an app on it.")
    out.append("")
    # THIS PARAGRAPH IS MEASURED, NOT WRITTEN. It used to state that nothing in
    # a gap record says which level it is about and that no record is credited —
    # true on the day the fourth test shipped, false from the moment a thread
    # tagged its first record, and it would have gone on saying it above a list
    # of credited levels. It is the second hardcoded claim in this renderer to
    # have needed that treatment.
    tagged = sum(len(e["claimed"]) for r in rows
                 for e in r["covered_entries"])
    credited = sum(1 for r in rows for e in r["covered_entries"]
                   for c in e["claimed"] if c[1])
    if not tagged:
        out.append("**No gap record claims a level yet, so every count here is a")
        out.append("floor.** A record can say which levels it covers and who was")
        out.append("asked, when, and what came back; none does, so a level this")
        out.append("report calls open may already have a record behind it. The")
        out.append("report understates an app rather than passing one.")
    else:
        out.append("**%d gap-record claim%s name%s a level, %d of which %s a"
                   % (tagged, "" if tagged == 1 else "s",
                      "s" if tagged == 1 else "", credited,
                      "carries" if credited == 1 else "carry"))
        out.append("dated ask that counts.** A level this report calls open and")
        out.append("that no record claims is still a floor. A claim that earns")
        out.append("nothing is printed under its level with the reason, rather")
        out.append("than passed.")
    out.append("")
    out.append("A level measured over every county, or every local government")
    out.append("above the standard's floor, is credited **unit by unit**: a record")
    out.append("names the county or unit it is about and the level closes only")
    out.append("when every unanswered one is either answered or has its own")
    out.append("credited record. One refusal cannot carry a whole tier.")
    out.append("")
    out.append("Raw gap-record counts are still reported and are deliberately")
    out.append("**not** a bar: a county that will never publish a map would keep a")
    out.append("state open forever while telling a reader nothing.")
    out.append("")
    out.append("Every instance the deploy publishes is scored, and a state joins")
    out.append("this table on the commit that publishes it: the fleet is read from")
    out.append("the tree and the deploy's own excludes, never from a list here. A")
    out.append("`-` is a test that does not apply to an instance, which is a")
    out.append("different thing from one it failed.")
    out.append("")
    out.append("| state | E.A.M.C. | counties | examined | districts | named | "
               "answered | files | maintained | covered |")
    out.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        if r["scored"]:
            counties = "%d" % r["total"]
            examined = "%d/%d" % (r["total"] if r["load_bearing"]
                                  else min(r["covered"], r["total"]), r["total"])
            if r["load_bearing"]:
                examined += " §"
            answered = ("all" if r["A"] else
                        ("%d short" % r["unanswered"] if r["unanswered"]
                         else "nothing recorded"))
            if r["A"] and r["answered_by"] == "record":
                answered = "by record"
        else:
            counties = examined = answered = "—"
        ok = sum(1 for e in r["covered_entries"]
                 if e["verdict"] in ("answered", "na"))
        out.append("| %s | **%s** | %s | %s | %d | %s | %s | %d | %s | %s |" % (
            r["tag"], letters(r), counties, examined,
            r["districts"], "{:,}".format(r["people"]), answered,
            r["rosters"],
            "all" if r["M"] else "%d without a job" % len(r["unmaintained"]),
            "all %d levels" % len(r["covered_entries"]) if r["C"]
            else "%d of %d levels" % (ok, len(r["covered_entries"])),
        ))
    out.append("")
    if any(r["load_bearing"] for r in rows):
        out.append("§ Examined in part by a record covering the whole state rather")
        out.append("than county by county. That is a weaker statement than a record")
        out.append("per county, so each one is named under its state below.")
        out.append("")
    for tag, why in sorted(NO_COUNTY_TIER.items()):
        out.append("- **%s** — no county frontier, so E and A do not apply. %s"
                   % (tag, why))
    out.append("")

    out.append("## What each state still needs")
    out.append("")
    for r in rows:
        done = is_done(r)
        # The mark is four tests since 2026-10-01, and this heading is the one
        # place it was still spelled with three. San Francisco is the first
        # instance to pass all four, so it is the first run where the stale
        # literal would have been read by anybody.
        out.append("### %s — %s" % (r["tag"], "**E.A.M.C.**" if done else letters(r)))
        out.append("")
        if not r["scored"]:
            out.append("- **E and A do not apply.** %s" % NO_COUNTY_TIER[r["tag"]])
            if r["districts"]:
                out.append("  The county roster it does ship is reported and not "
                           "gated: %d district(s), %s people named."
                           % (r["districts"], "{:,}".format(r["people"])))
            out.append("  The mark therefore rests on Maintained alone.")
        if r["load_bearing"]:
            out.append("- **Examined by a statewide record:** %s account%s for "
                       "every county in the state, which is what Examined rests "
                       "on here: %d of %d counties are covered one at a time — "
                       "served by a roster or named individually — and the rest "
                       "by the record%s. That is a weaker statement, and it is "
                       "the honest one while the answer is the same in every "
                       "county."
                       % (", ".join("`%s`" % g for g in r["load_bearing"]),
                          "s" if len(r["load_bearing"]) == 1 else "",
                          min(r["covered"], r["total"]), r["total"],
                          "" if len(r["load_bearing"]) == 1 else "s"))
        if r["scored"] and r["A"] and r["answered_by"] == "record":
            out.append("- **Answered by record, not by name.** No county district "
                       "is drawn yet, so nothing is left silent — the absence is "
                       "written down. That is the standard's third branch and it "
                       "is a weaker guarantee than a named seat: the mark will "
                       "move to names the day the districts ship.")
        if done:
            out.append("")
            out.append("Every test that applies is met. Expansion is finished;")
            out.append("this instance is in maintenance.")
            out.append("")
            out.extend(covered_lines(r))
            out.append("")
            for rel, workflow in r["watched"]:
                out.append("- **Watched, not rewritten:** `%s` is refreshed by no "
                           "job because it cannot safely be — `%s` checks its "
                           "source weekly and opens an issue when it moves. "
                           "That is a weaker guarantee than a rewrite: it tells "
                           "you the source changed and a person still has to "
                           "act." % (rel, workflow))
            if r["watched"]:
                out.append("")
            continue
        if r["E"] is False:
            out.append("- **Examined: no.** %d of %d counties have neither a roster "
                       "nor a gap record naming them. They are not blocked — they "
                       "are unlooked-at, which is the one state this bar refuses."
                       % (r["unexamined"], r["total"]))
        if r["A"] is False and r["answered_by"] is None:
            out.append("- **Answered: no.** The app's county tier draws no "
                       "district and records no absence, so a reader is told "
                       "neither a name nor a reason.")
        elif r["A"] is False:
            out.append("- **Answered: no.** %d district(s) name nobody, are not "
                       "marked vacant and carry no note: %s"
                       % (r["unanswered"], "; ".join(r["unanswered_names"])))
        for rel, workflow in r["watched"]:
            out.append("- **Watched, not rewritten:** `%s`, by `%s` — counts "
                       "for Maintained, and is a weaker guarantee than a "
                       "rewrite." % (rel, workflow))
        if r["planned"]:
            out.append("- **Under a WATCH.md plan (%d):** re-checked on a "
                       "stated cadence rather than by a job — %s"
                       % (len(r["planned"]),
                          ", ".join("`%s`" % (x if x.endswith("/")
                                                 else os.path.basename(x))
                                    for x, _ in r["planned"])))
        if not r["M"]:
            by = {}
            for _, kind, _ in r["unmaintained"]:
                by[kind] = by.get(kind, 0) + 1
            out.append("- **Maintained: no.** %d file(s) under no scheduled job "
                       "at all, neither rewriting nor watching — %d boundary, "
                       "%d census, %d structure, **%d naming people**. %s"
                       % (len(r["unmaintained"]),
                          by.get("geometry", 0), by.get("census", 0),
                          by.get("structure", 0), by.get("roster", 0),
                          "No officeholder is going stale here; what these want "
                          "is a stated re-check cadence, not a weekly scraper."
                          if not by.get("roster") else
                          "The roster files are the urgent ones: a name goes "
                          "wrong the week a member leaves."))
            for rel, kind, n in r["unmaintained"]:
                if kind == "roster":
                    out.append("  - `%s` — names **%d** people and nothing "
                               "refreshes them, so they go stale at the speed "
                               "that body turns over." % (rel, n))
                elif kind == "geometry":
                    out.append("  - `%s` — **%d** boundary feature(s), naming "
                               "nobody. It rots on reapportionment rather than "
                               "on officeholder churn, so a weekly job would "
                               "be a guaranteed no-op; what it wants is a "
                               "`WATCH.md` row stating when the lines are "
                               "re-checked." % (rel, n))
                elif kind == "census":
                    out.append("  - `%s` — **%d** file(s), served by URL prefix "
                               "rather than listed, naming nobody. It is "
                               "superseded by the next decennial census and by "
                               "nothing else, so what it wants is a `WATCH.md` "
                               "row carrying that date." % (rel, n))
                else:
                    out.append("  - `%s` — names nobody; it carries structure "
                               "(seat counts, addresses, links). Slower to "
                               "rot, on link rot rather than on officeholder "
                               "churn, and still refreshed by nothing." % rel)
        out.extend(covered_lines(r))
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def check_workflows(paths, staged):
    """A scheduled workflow that rewrites a roster this report COUNTS must
    regenerate it and commit it.

    The same rule `build_county_pages.py`, `build_officeholder_tables.py` and
    `build_concept_pages.py` already enforce, and it arrived here the way those
    three predict: #1093's bot PR went red on `build_eam_status.py --check`
    because Sangamon lost a member to a vacancy, the `people` figure moved, and
    no roster workflow rebuilds this file. The bot wrote the change and a human
    had to work out why a refresh of one county's names failed a gate about the
    whole fleet.

    THE SURFACE IS MEASURED, NEVER LISTED. The three siblings each carry a
    hand-written `counts` list because each owns a handful of pages; this report
    reads every roster `build_county_pages`' adapters read — 71 files across
    four instances on the day this was written — and that set moves whenever a
    county ships. So the surface is `load_rosters()`'s own `paths`, and the
    workflows are whatever `refreshed_by()` already says stages one. A list
    here would go stale at the speed of the Illinois frontier.

    IT IS THE ADAPTER SURFACE AND NOT EVERY `data/app` FILE, which Michigan
    measured rather than assumed (`mi/BOARD.md`, 2026-09-22): of its six weekly
    roster jobs only `update-mi-commissioner-roster.yml` moves the figure,
    because `people` counts the districts these adapters name and not every
    officeholder an instance ships. Requiring the step on the other five would
    ask 59 workflows across the fleet to regenerate a file they cannot change.
    """
    surface = sorted({os.path.relpath(p, REPO_ROOT)
                      for tag in paths for p in paths[tag]})
    named = {}
    for rel in surface:
        for workflow in refreshed_by(rel, staged):
            named.setdefault(workflow, set()).add(rel)
    for workflow in sorted(named):
        text = open(os.path.join(REPO_ROOT, workflow), encoding="utf-8").read()
        lines = text.splitlines()
        rosters = ", ".join(sorted(named[workflow]))
        # RUN and STAGED, never merely MENTIONED, for both of these. The step
        # this gate asks for carries a comment naming the script and the file,
        # so a plain `in text` test is satisfied by that comment and passes a
        # workflow that regenerates nothing — measured on this gate's own
        # first draft, where the second check was vacuous for exactly that
        # reason and a negative test caught it.
        if not any(line.strip() == "python3 scripts/build_eam_status.py"
                   for line in lines):
            fail("%s rewrites %s and never regenerates docs/EAM_STATUS.md — "
                 "add a step running python3 scripts/build_eam_status.py and "
                 "`git add docs/EAM_STATUS.md`, or its next refresh that moves "
                 "a count fails this gate on the bot's own pull request"
                 % (workflow, rosters))
        if not any("git add " in line and "docs/EAM_STATUS.md" in line
                   for line in lines):
            fail("%s regenerates docs/EAM_STATUS.md and never commits it — "
                 "add it to that job's `git add`" % workflow)
    if not named:
        fail("no scheduled workflow stages any of the %d rosters this report "
             "counts, which cannot be true — the surface or the staged-path "
             "reader has broken" % len(surface))
    print("build-eam-status: %d scheduled workflows regenerate this report"
          % len(named))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="fail if docs/EAM_STATUS.md is not what this run produces")
    ap.add_argument("--report", action="store_true",
                    help="print the table and write nothing")
    ap.add_argument("--selftest", action="store_true",
                    help="hold shape_of to files whose shape is settled")
    args = ap.parse_args()

    if args.selftest:
        selftest()
        return

    check_geometry_names_nobody()
    check_undeclared_name_keys()
    counties, paths, B = load_rosters()
    check_workflows(paths, staged_paths())
    rows = measure(counties, paths, B)
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
    for r in rows:
        short = [e for e in r["covered_entries"]
                 if e["verdict"] not in ("answered", "na")]
        print("build-eam-status: %s — covered: %d of %d expected level(s)%s"
              % (r["tag"], len(r["covered_entries"]) - len(short),
                 len(r["covered_entries"]),
                 "" if not short else "; not answered: " +
                 ", ".join("%d %s" % (e["number"], e["key"]) for e in short)))
    done = [r["tag"] for r in rows if is_done(r)]
    print("build-eam-status: OK — %s; %s" % (
        marks,
        ("in maintenance: " + ", ".join(done)) if done
        else "no instance is E.A.M.C. yet"))


if __name__ == "__main__":
    main()
