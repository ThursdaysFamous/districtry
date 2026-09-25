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
    people = sum(1 for rec in _records(doc)
                 if "name" in rec and any(f in rec for f in PERSON_FIELDS))
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
)


def selftest():
    """Hold `shape_of` to files whose shape is settled.

    This module's own record says it was corrected four times on the day it
    was built and had no self-test that would have caught any of them. The
    fifth correction was the classifier, so the classifier gets one.
    """
    bad = 0
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
        fail("%d shape case(s) failed" % bad)
    print("build-eam-status: selftest OK — %d shape case(s)" % len(SHAPE_CASES))


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


def watch_rows(tag):
    """{filename: the WATCH.md row's cadence cell} for rows that state a when."""
    path = os.path.join(REPO_ROOT, WATCH_FILE.get(tag, os.path.join(tag, "WATCH.md")))
    if not os.path.exists(path):
        return {}
    out, last_when = {}, None
    for line in open(path, encoding="utf-8"):
        if not line.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells or set(cells[0]) <= set("-: "):
            continue
        when = None
        if WHEN.search(cells[0]):
            when = cells[0]
            last_when = when
        elif SAME_AS_ABOVE.match(cells[0]) and last_when:
            when = "%s (%s)" % (cells[0], last_when)
        if not when:
            continue
        for name in re.findall(r"[A-Za-z0-9_.-]+\.json", line):
            out.setdefault(name, when)
        # A FOLDER CLASS CARRIES NO FILENAME, so the `.json` scan above cannot
        # see it and a row written for one would count for nothing while
        # looking exactly like a plan. Matched on the class's own rel path,
        # with or without its trailing slash.
        for rel in PREFIX_KIND:
            if rel in line or rel.rstrip("/") in line:
                out.setdefault(rel, when)
    return out


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


def measure(counties, paths, B):
    staged = staged_paths()
    watchers = watcher_texts()
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

        # THE SURFACE IS EVERY DATA FILE THE APP READS, not the roster files
        # alone. Wisconsin found that hole: M flagged a 72-record directory of
        # seat counts and missed county-supervisory-districts.json, the 1,590
        # districts it is derived from and the file the whole county-board card
        # is drawn on. A bar that fails the restatement and passes the source
        # is not measuring what it claims to.
        surface = sorted(
            {os.path.relpath(p, REPO_ROOT) for p in set(paths.get(tag, ()))} |
            set(app_data_files(tag)) | set(prefix_classes(tag)))

        planned_rows = watch_rows(tag)
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
            when = planned_rows.get(rel if rel.endswith("/")
                                    else os.path.basename(rel))
            if when:
                planned.append((rel, when))
                continue
            # What the unrefreshed file IS, which is what decides how fast it
            # rots. Read off the file's own shape rather than the adapter's
            # output: a directory of seat counts contributes no districts, so
            # the adapter view cannot tell it from an empty one.
            unmaintained.append((rel,) + shape_of(os.path.join(REPO_ROOT, rel)))

        rows.append(dict(
            tag=tag, total=total, ring=ring,
            served=len(served), recorded=len(recorded), covered=len(covered),
            unexamined=unexamined,
            districts=districts, people=people,
            unanswered=unanswered, unanswered_names=unanswered_names,
            rosters=len(surface), unmaintained=unmaintained,
            watched=watched, planned=planned,
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
    out.append("| state | E.A.M. | counties | examined | districts | named | answered | files | maintained |")
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
        if not r["E"]:
            out.append("- **Examined: no.** %d of %d counties have neither a roster "
                       "nor a gap record naming them. They are not blocked — they "
                       "are unlooked-at, which is the one state this bar refuses."
                       % (r["unexamined"], r["total"]))
        if not r["A"]:
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
    done = [r["tag"] for r in rows if r["E"] and r["A"] and r["M"]]
    print("build-eam-status: OK — %s; %s" % (
        marks,
        ("in maintenance: " + ", ".join(done)) if done
        else "no instance is E.A.M. yet"))


if __name__ == "__main__":
    main()
