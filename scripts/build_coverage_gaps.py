#!/usr/bin/env python3
"""
Emit data/app/coverage-gaps.json from the guidebook's GUIDEBOOK:BEGIN gaps block.

Why the guidebook is the source and not a hand-kept data file: every gap in it
already had to be recorded there with its rationale ("a deliberate 'we will not
ship this here' is recorded, never implied" — the guidebook's own maintenance
contract). Keeping the machine truth in the same document as the prose means a
gap cannot be closed in one place and left open in the other, and it follows the
coverage-map precedent that fleet_status.py already parses.

The app reads the emitted file to drive its Data gaps panel. `--check` is the CI
drift gate: it re-emits and compares, so editing the guidebook without
regenerating (or vice versa) fails the build rather than shipping a panel that
disagrees with the document of record.

TWO AUDIENCES, TWO SETS OF FIELDS. A gap record serves a maintainer (what was
measured, on what date, against which host, and why the obvious route is closed)
and a voter (what won't show up on my card, and why). Those are not the same
text, and for a year they were: the panel printed `blocker` verbatim, which runs
to ten thousand characters on the harder counties, so the one surface whose job
is to make absence legible was the least legible thing in the app.

So the fields are split by audience:
  - READER FIELDS — `summary`, `why`, `wanted` — are the only ones emitted. Each
    is capped at 240 characters and linted for the house style of the record
    (shouting, hostnames, ISO dates), because a cap is the only thing that keeps
    a research note from growing back into the panel one edit at a time.
  - THE RECORD — `blocker` — is required, unbounded, and NEVER shipped. It stays
    in the guidebook where the next maintainer looks, so nothing about the data
    journey is lost; it simply stops being read aloud to somebody who only wants
    to know who represents them.

Validation is deliberately strict about the things a reader would be misled by:
  - every entry needs a stable id, an area, a summary, a plain-language `why`, a
    measured blocker, and a `wanted` line, because a gap with no `wanted` invites
    re-sending a source that was already rejected;
  - `kind` must be one of no-source / blocked / data-quality — the two classes
    the panel is scoped to, plus `blocked` for a source that exists but refuses
    automation;
  - `layer` must name a real registered layer (or be null for a concept not yet
    built), so a gap can never point at a toggle that does not exist;
  - `counties` must name outline files that actually ship, since that is what
    makes the gap location-aware.

The guidebook lives in the CHICAGO repo only — it is a fleet document, and a
second copy in a sibling would be the drift trap docs/ENGINE_SYNC.md warns about.
So a sibling fork does NOT carry this script; its data/app/coverage-gaps.json is
generated from here with --metro/--out and lands in the fork through its engine
bump PR.

Usage:
    python3 scripts/build_coverage_gaps.py
    python3 scripts/build_coverage_gaps.py --check
    # emit a sibling fork's file from Chicago's guidebook:
    python3 scripts/build_coverage_gaps.py --metro nyc --out ny/data/app/coverage-gaps.json
"""

import argparse
import datetime
import json
import os
import re
import sys
from scraper_common import make_fail  # noqa: E402  (shared machinery — do not fork)
from gap_counts import resolve_record  # noqa: E402  (one reader for both gates)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUIDEBOOK = os.path.join(REPO_ROOT, "docs", "DATA_LAYER_GUIDEBOOK.md")
WORKSHEET = os.path.join(REPO_ROOT, "metro-worksheet.json")
OUT_PATH = os.path.join(REPO_ROOT, "il", "data", "app", "coverage-gaps.json")
APP_DATA_DIR = os.path.join(REPO_ROOT, "il", "data", "app")

GAPS_RE = re.compile(
    r"<!-- ==== GUIDEBOOK:BEGIN gaps ==== -->\s*```json\s*(.*?)\s*```",
    re.S,
)
KINDS = ("no-source", "blocked", "data-quality")
REQUIRED = ("id", "concept", "area", "kind", "summary", "why", "blocker", "wanted")
# Field order in the emitted file. Fixed so the output is byte-stable and --check
# compares content rather than dict ordering. `blocker` is deliberately absent:
# it is the maintainer's record, kept in the guidebook and never shipped.
FIELD_ORDER = ("id", "kind", "concept", "area", "layer", "counties",
               "everyCounty", "summary", "why", "wanted")

# `everyCounty` SAYS THIS RECORD ACCOUNTS FOR EVERY COUNTY IN THE STATE, and it
# is a different claim from a `counties` tag rather than a shortcut for one.
#
# A `counties` tag is a promise the Data gaps panel can LOCATE that county — it
# fetches data/app/<slug>-county-outline.json to decide whether the gap is where
# a reader clicked, which is why the check above refuses a tag with no outline.
# EXAMINED asks something else entirely: is every county in the state either
# served by a roster or named by a record saying why not. A state whose answer
# is uniform writes that once, over the whole state, and ships no outlines at
# all — Minnesota's county-commissioner record reads "Minnesota — all 87
# counties" and Kentucky's fiscal-court record "Kentucky — all 120 counties".
#
# Read through the tags alone, both states scored 0 counties examined out of 87
# and 120, which is false and points the wrong way: it would send a state to
# ship 87 county outlines to satisfy a bookkeeping gate, when the outlines exist
# for the reader's panel and the panel has nothing to show there. So the claim
# is DECLARED on the record, never inferred from the `area` prose, because every
# instrument in this repository that has read a claim out of prose has been
# wrong about it at least once.
#
# It is refused beside a `counties` list: a record either accounts for the whole
# state or names which counties it covers, and one saying both is one of the two
# by accident. `build_eam_status.py` prints every record it counts this way on
# each run, and reports per-county coverage separately, so a statewide
# declaration cannot quietly stand in for county-by-county work.
EVERY_COUNTY = "everyCounty"

# `covers` AND `ask` ARE HOW A RECORD EARNS CREDIT UNDER THE FOURTH TEST, and
# both are maintainer fields: neither is in FIELD_ORDER, so neither ships to a
# reader. `docs/DONE_STANDARD.md` lets a written record stand in for a level the
# app cannot answer, but only once somebody was actually asked — and until these
# fields existed nothing in a record said WHICH level it covered or WHICH ask it
# rested on, so `build_eam_status.py` credited none of them and every count it
# published was a floor.
#
# `covers` names the expected levels, by the key `build_eam_status.FUNCTIONS`
# uses. THE KEYS ARE NOT CHECKED HERE and that is deliberate: that tuple is the
# standard's thirteen entries and it has one owner, so a second copy of the list
# in this file is the two-readers defect this repository keeps paying for.
# `build_eam_status.py` refuses a key it does not know, by name, in CI.
#
# `ask` is the ledger entry, on the record itself, because THE RECORD IS THE
# LEDGER: docs/ASK_DRAFTS.md step 2 says the send date is written "in the
# relevant gap record in docs/DATA_LAYER_GUIDEBOOK.md", and that prose is all
# there has ever been. These fields do not replace it; they make the part a
# program has to agree with machine-readable.
#
# THE THIRTY DAYS ARE CHECKED AGAINST A STATED OUTCOME, NEVER COMPUTED INTO ONE.
# The standard counts silence once we have asked, followed up once and waited
# thirty days from the follow-up. A reader of the clock would flip this record
# from "no credit" to "credit" on day thirty with nothing edited, which moves a
# generated document by the calendar and fails `--check` on a morning nobody
# touched the tree — the shape `dropped_rings.py` records as a ceiling that can
# never fail, pointing the other way. So the thread WRITES `unresponsive` once
# it is true, and this gate refuses the claim while the dates do not support it.
# The verdict can then only ever become true, and the arithmetic is still
# measured rather than trusted.
#
# `pending` IS AN OUTCOME BECAUSE A SENT ASK HAS A STATE, and until 2026-10-01
# it had nowhere to live: `outcome` was required and its three values were all
# terminal, so a letter that had gone out and was waiting could not be written
# down at all. The advice this gate printed — "leave the outcome off until it is
# true" — described a record the gate itself refused. Michigan put its send
# dates in `blocker` prose instead, which is the free-text state these fields
# exist to end, and the day Adam sent about forty letters that became the
# ordinary case rather than one state's workaround.
#
# A PENDING ASK NEVER FAILS BY THE CALENDAR AND NEVER EARNS CREDIT. The two are
# the same rule read from either side: nothing about a pending ask may change
# what a generated file says, because a document that moves by the date fails
# `--check` on a morning nobody touched the tree. So the clock is computed and
# PRINTED — days since the ask, days since the follow-up, whether either is ripe
# — on this gate's own stdout, where a reader of the run sees it and no
# committed byte depends on it. Turning `pending` into `unresponsive` stays a
# thread's edit, which the dates below still have to support.
COVERS = "covers"
ASK = "ask"
ASK_OUTCOMES = ("pending", "refused", "unresponsive", "answered")
ASK_SILENCE_DAYS = 30

# The three fields a voter reads, and the budget each gets. 240 characters is
# about two lines in the panel — enough for a plain sentence and not enough for
# a research note.
READER_FIELDS = ("summary", "why", "wanted")
READER_MAX = 240
# House-style tells that belong in `blocker` and read as noise on a card.
SHOUTING_RE = re.compile(r"\b[A-Z]{3,}\b[ ,]+\b[A-Z]{3,}\b")
HOSTNAME_RE = re.compile(r"\b[a-z0-9][a-z0-9-]*\.(?:gov|com|org|net|us|edu|io)\b")
ISO_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
URL_RE = re.compile(r"https?://")


fail = make_fail("build-coverage-gaps")


def load_gaps():
    with open(GUIDEBOOK, encoding="utf-8") as f:
        m = GAPS_RE.search(f.read())
    if not m:
        fail("no GUIDEBOOK:BEGIN gaps block in docs/DATA_LAYER_GUIDEBOOK.md")
    try:
        return json.loads(m.group(1))
    except ValueError as e:
        fail("gaps block is not valid JSON: %s" % e)


def worksheet():
    with open(WORKSHEET, encoding="utf-8") as f:
        return json.load(f)


def known_layer_ids(w):
    return {l["id"] for l in w["layers"]}


def shipped_outline_slugs(app_data_dir=None):
    d = app_data_dir or APP_DATA_DIR
    if not os.path.isdir(d):
        return None
    return {f[: -len("-county-outline.json")]
            for f in os.listdir(d) if f.endswith("-county-outline.json")}


def sibling_surfaces(out_path):
    """The layer ids and outline slugs of the instance an --out path points
    into, so a sibling's file is validated against ITS OWN app rather than
    against nothing.

    This is the hole that shipped a broken panel. Both per-fork checks used to
    be skipped whenever `--metro` named someone else, because the only
    worksheet and data dir this script knew were Illinois's. So Wisconsin's
    gaps were emitted for weeks with never a slug or layer id checked — and
    when all ten shipped with EMPTY counties, nothing said so. An instance
    laid out like this repo's own (`<root>/data/app/coverage-gaps.json`
    beside `<root>/metro-worksheet.json`) is now measured against itself; a
    path shaped like anything else falls back to skipping, exactly as before.
    """
    app_dir = os.path.dirname(os.path.abspath(out_path))
    inst = os.path.dirname(os.path.dirname(app_dir))
    ws = os.path.join(inst, "metro-worksheet.json")
    if not (os.path.basename(app_dir) == "app" and os.path.exists(ws)):
        return None, None
    with open(ws, encoding="utf-8") as f:
        sibling = json.load(f)
    return known_layer_ids(sibling), shipped_outline_slugs(app_dir)


def reader_problems(where, e):
    """Style problems in the three fields a voter actually reads.

    Every rule here has a counter-example in this file's own history: the panel
    once printed a 10,600-character blocker as its "Why" line, hostnames and
    HTTP status codes and ALL-CAPS findings included. None of that is wrong in
    the record; all of it is wrong on a card read by somebody who wants to know
    who represents them. Keep the finding, move it to `blocker`.
    """
    out = []
    for key in READER_FIELDS:
        text = str(e.get(key) or "").strip()
        if not text:
            continue                     # absence is REQUIRED's business
        if len(text) > READER_MAX:
            out.append("%s: %s is %d characters (max %d) — say it plainly here "
                       "and move the detail to `blocker`"
                       % (where, key, len(text), READER_MAX))
        if URL_RE.search(text) or HOSTNAME_RE.search(text):
            out.append("%s: %s names a hostname or URL — readers get the "
                       "publisher from the card, not from this line" % (where, key))
        if ISO_DATE_RE.search(text):
            out.append("%s: %s carries an ISO date — dates belong in `blocker`; "
                       "write \"since 2021\" if the timing matters to a reader"
                       % (where, key))
        if SHOUTING_RE.search(text):
            out.append("%s: %s shouts in capitals — that is record voice, not "
                       "reader voice" % (where, key))
    return out


def resolve_all(entries, root=None):
    """Every record with its reader fields resolved, and what went wrong.

    THE RESOLVED TEXT IS THE SUBJECT OF EVERY CHECK BELOW, which is the third
    refusal in the manager's 2026-09-26 ruling and Michigan's widening of it.
    A record is checked and rendered through the same resolution, so the length
    READER_MAX measures, the hostname and ISO-date and shouting tests, and the
    counted-prose comparison all read what a reader is actually served. Holding
    READER_MAX to the AUTHORED text would refuse the first record the form
    exists for: measured 2026-09-29, `mi-commissioner-roster`'s summary is 254
    characters written with its three tokens and 230 resolved — over the
    ceiling in the source file and under it on the card.

    A RECORD WHOSE RESOLUTION FAILS IS RETURNED AS AUTHORED rather than
    dropped, so its other problems are reported in the same run. The build
    still fails, because the failure is in `problems`.

    A record with no token comes back unchanged, which is why introducing this
    left all six instances' shipped files byte-identical.
    """
    problems, out = [], []
    for i, e in enumerate(entries):
        where = e.get("id") or "entry %d" % i
        got = resolve_record(e, READER_FIELDS, where, problems.append, root=root)
        out.append(e if got is None else dict(e, **got))
    return out, problems


def token_budgets(authored, resolved):
    """One line per token-bearing field: what it resolves to, against the ceiling.

    Michigan's ask, and it costs nothing: once a field's length is decided by a
    measurement rather than by its own characters, an author can no longer
    budget it by eye. Measured 2026-09-29, six of the eight declared reader
    fields in the fleet sit within 35 characters of the 240 ceiling and the
    tightest has 7, so this is a live budget rather than a theoretical one.
    """
    lines = []
    for source, shown in zip(authored, resolved):
        for key in READER_FIELDS:
            text = source.get(key)
            if not isinstance(text, str) or "{" not in text:
                continue
            got = shown.get(key)
            if not isinstance(got, str):
                continue
            lines.append("  %s %s: %d of %d characters resolved (%d authored)"
                         % (source.get("id"), key, len(got), READER_MAX, len(text)))
    return lines


def _iso(value):
    """A real ISO date, or None. `datetime` is stdlib, which this script stays in."""
    if not isinstance(value, str):
        return None
    try:
        return datetime.date(*(int(p) for p in value.split("-")))
    except (ValueError, TypeError):
        return None


def ask_problems(where, e):
    """Problems with this record's `covers`/`ask` pair.

    A record may carry `covers` with no `ask`: that is the ordinary state of a
    gap nobody has written to yet, it is legal, and `build_eam_status.py`
    reports it as earning nothing rather than passing it — which is what
    `docs/DONE_STANDARD.md` asks for in as many words.

    What is refused is a claim the dates do not support, in either direction.
    """
    problems = []
    covers, ask = e.get(COVERS), e.get(ASK)
    if covers is not None:
        if (not isinstance(covers, list) or not covers
                or not all(isinstance(c, str) and c.strip() for c in covers)):
            problems.append(
                "%s: %s must be a non-empty list of expected-level keys, never %r"
                % (where, COVERS, covers))
        elif len(set(covers)) != len(covers):
            problems.append("%s: %s names the same claim twice: %r"
                            % (where, COVERS, covers))
        else:
            # AN ENTRY MAY NAME A UNIT, AS `<level key>:<unit id>`, and for a
            # level measured over every county or every large town it MUST —
            # otherwise one refusal from one city would carry a whole state's
            # local tier. Which levels are measured that way is
            # build_eam_status.py's to say (it owns the thirteen), so only the
            # SHAPE is held here: one colon, and neither side empty.
            for c in covers:
                if ":" not in c:
                    continue
                key, _sep, unit = c.partition(":")
                if not key.strip() or not unit.strip() or ":" in unit:
                    problems.append(
                        "%s: %s entry %r is not `<level key>:<unit id>` — one "
                        "colon, with a level key before it and a unit id after"
                        % (where, COVERS, c))
    if ask is None:
        return problems
    if not isinstance(ask, dict):
        problems.append("%s: %s must be an object, never %r" % (where, ASK, ask))
        return problems
    extra = sorted(set(ask) - {"who", "asked", "followedUp", "outcome"})
    if extra:
        problems.append("%s: %s has no field(s) %s" % (where, ASK, ", ".join(extra)))
    if not str(ask.get("who") or "").strip():
        problems.append(
            "%s: %s needs `who` — the standard counts an ask made BY NAME, and "
            "'the county' is not a desk anybody wrote to" % (where, ASK))
    asked = _iso(ask.get("asked"))
    if asked is None:
        problems.append("%s: %s needs `asked` as a YYYY-MM-DD date, not %r"
                        % (where, ASK, ask.get("asked")))
    outcome = ask.get("outcome")
    if outcome not in ASK_OUTCOMES:
        problems.append("%s: %s outcome %r is not one of %s"
                        % (where, ASK, outcome, list(ASK_OUTCOMES)))
    followed = None
    if ask.get("followedUp") is not None:
        followed = _iso(ask.get("followedUp"))
        if followed is None:
            problems.append("%s: %s `followedUp` is not a YYYY-MM-DD date: %r"
                            % (where, ASK, ask.get("followedUp")))
    today = datetime.date.today()
    for field, value in (("asked", asked), ("followedUp", followed)):
        if value is not None and value > today:
            problems.append("%s: %s `%s` is %s, which is in the future"
                            % (where, ASK, field, value))
    if asked and followed and followed < asked:
        problems.append(
            "%s: %s was followed up on %s and asked on %s — a follow-up comes "
            "after the ask" % (where, ASK, followed, asked))
    if outcome == "unresponsive":
        if followed is None:
            problems.append(
                "%s: %s claims `unresponsive` and records no follow-up. The "
                "standard counts silence only after one follow-up, because a "
                "follow-up is a recovery mechanism and not a nudge — one Clerk "
                "answered on the third attempt" % (where, ASK))
        elif (today - followed).days < ASK_SILENCE_DAYS:
            problems.append(
                "%s: %s claims `unresponsive` %d day(s) after its follow-up of "
                "%s, and the standard asks for %d. Record `pending` until it is "
                "true; this gate exists so the claim cannot be made early"
                % (where, ASK, (today - followed).days, followed,
                   ASK_SILENCE_DAYS))
    if outcome == "answered" and covers:
        problems.append(
            "%s: %s was answered and %s still claims %s. An answered ask means "
            "the data is obtainable, so the work is to use it rather than to "
            "record the level as covered"
            % (where, ASK, COVERS, ", ".join(covers)))
    return problems


def pending_ask_lines(entries):
    """One line per ask that has been sent and is waiting, with its own clock.

    PRINTED, NEVER WRITTEN. Everything here is derived from today's date, so it
    cannot reach a committed file without making that file's drift check fail on
    a morning nobody edited the tree — the trap `dropped_rings.py` records for a
    ceiling recomputed every run, pointing the other way. Keeping the clock on
    stdout gives a thread the arithmetic it would otherwise do by hand while
    leaving every verdict where a person put it.

    `ripe` says only that the dates now support the next step. It is an
    invitation to go and look, not a verdict: the standard counts silence, and
    an inbox nobody has checked is not silence.
    """
    today = datetime.date.today()
    lines = []
    for i, e in enumerate(entries):
        ask = e.get(ASK)
        if not isinstance(ask, dict) or ask.get("outcome") != "pending":
            continue
        where = e.get("id") or "entry %d" % i
        asked = _iso(ask.get("asked"))
        followed = _iso(ask.get("followedUp"))
        if followed is not None:
            days = (today - followed).days
            left = ASK_SILENCE_DAYS - days
            state = ("ripe for `unresponsive`" if left <= 0
                     else "%d day(s) to go before `unresponsive`" % left)
            lines.append(
                "  ASK   %s: %s, followed up %s (%d day(s) ago) — %s"
                % (where, ask.get("who"), followed, days, state))
        elif asked is not None:
            days = (today - asked).days
            state = ("ripe for a follow-up" if days >= ASK_SILENCE_DAYS
                     else "no follow-up sent yet")
            lines.append("  ASK   %s: %s, asked %s (%d day(s) ago) — %s"
                         % (where, ask.get("who"), asked, days, state))
        else:
            lines.append("  ASK   %s: %s, pending with no readable date"
                         % (where, ask.get("who")))
    return lines


ASK_DRAFTS = os.path.join(REPO_ROOT, "docs", "ASK_DRAFTS.md")
ASK_HEAD_RE = re.compile(r"^##+ Ask ([^\n\u2014]+?)\s*(?:\u2014|$)", re.M)
# A citation is `Ask 12` or `Ask il-ford-board-map`. Prose like "Ask the county"
# is not a citation and is deliberately not matched.
ASK_CITE_RE = re.compile(r"\bAsk ([0-9]+|[a-z]{2}-[a-z0-9-]+)\b")


def ask_reference_problems(entries):
    """Every ask a gap record cites exists, and no two asks share an id.

    WHY THIS EXISTS. `docs/ASK_DRAFTS.md` numbers asks in one sequence and gap
    records cite them in prose, so two branches each drafting "the next ask"
    both write the same number — and on 2026-10-01 three did, two of them
    claiming Ask 33. Git merges that silently: both headings land, and whoever
    renumbers one afterwards moves it out from under every record citing it.
    Nothing compared the two files.

    WHAT TO DO INSTEAD, for a NEW ask: take an id that names its subject,
    `Ask <state tag>-<short slug>` — `Ask il-ford-board-map` — rather than the
    next number. Two branches cannot collide on it, and it cannot be renumbered
    out from under a record. The existing numbered asks KEEP their numbers:
    several have been sent and cited in correspondence, and renumbering a letter
    somebody has already received would be worse than the inconsistency.

    WHAT THIS DOES NOT SEE, stated rather than implied: it reads citations in
    the gaps block alone, which is the surface this file owns. An ask cited only
    in a doc or a builder comment is not checked here. And it cannot tell a
    citation pointing at the WRONG ask of two that both exist — only that both
    numbers resolve. The uniqueness half is what forces a person to look.
    """
    problems = []
    if not os.path.exists(ASK_DRAFTS):
        # Not every fork carries the drafts file, and its absence is not this
        # gate's business to rule on.
        return problems
    with open(ASK_DRAFTS, encoding="utf-8") as fh:
        drafts = fh.read()
    ids = [h.strip() for h in ASK_HEAD_RE.findall(drafts)]
    for one in sorted({i for i in ids if ids.count(i) > 1}):
        problems.append(
            "docs/ASK_DRAFTS.md has %d asks numbered `Ask %s`. Two branches "
            "took the same next number; give the newer one a subject id "
            "(`Ask <state>-<slug>`) rather than renumbering it, so no record "
            "citing the old number is left pointing at the wrong ask."
            % (ids.count(one), one))
    known = set(ids)
    for e in entries:
        where = "gap `%s`" % (e.get("id") or "<unnamed>")
        text = " ".join(str(v) for v in e.values() if isinstance(v, str))
        for cited in sorted(set(ASK_CITE_RE.findall(text))):
            if cited not in known:
                problems.append(
                    "%s cites `Ask %s` and docs/ASK_DRAFTS.md has no such ask. "
                    "Either the ask was renumbered under this record or it was "
                    "withdrawn; say which in the record rather than leaving a "
                    "citation that resolves to nothing." % (where, cited))
    return problems


def validate(entries, layer_ids, outlines):
    problems, seen = [], set()
    for i, e in enumerate(entries):
        where = e.get("id") or "entry %d" % i
        for key in REQUIRED:
            if not str(e.get(key) or "").strip():
                problems.append("%s: missing %s" % (where, key))
        problems.extend(reader_problems(where, e))
        if e.get("id") in seen:
            problems.append("%s: duplicate id" % where)
        seen.add(e.get("id"))
        if e.get("kind") not in KINDS:
            problems.append("%s: kind %r not one of %s" % (where, e.get("kind"), list(KINDS)))
        layer = e.get("layer")
        if layer_ids is not None and layer is not None and layer not in layer_ids:
            problems.append("%s: layer %r is not a registered layer id" % (where, layer))
        # EVERY COUNTY TAG NEEDS ITS OUTLINE, WITH NO EXEMPTION FOR AN INSTANCE
        # THAT SHIPS NONE — and this line was relaxed to `if outlines` earlier
        # on 2026-09-22 and put back the same day, which is the whole lesson.
        #
        # The relaxation was written to fix a real problem: an instance with no
        # outlines returns an EMPTY SET, the check refused every tag it could
        # ever write, and EXAMINED was therefore unreachable by construction for
        # Michigan (0 outlines) and nearly so for Iowa (2 of 99). Michigan found
        # it by promoting 35 measured blockers into gap records and watching its
        # score sit still at 48 of 83.
        #
        # But skipping the check is not what "untaggable" needed. Michigan
        # tagged its 35 counties, the tags passed unchecked, and the Data gaps
        # panel broke in the one direction it exists to prevent: `appliesHere`
        # fetches data/app/<slug>-county-outline.json, all 35 404'd,
        # `mappable` flipped true anyway, and a reader standing in one of those
        # counties was told "Nothing recorded is missing where you clicked".
        # THE EMPTY ARRAYS HAD BEEN PROTECTING THE READER BY ACCIDENT.
        #
        # Adam ruled the real fix on the same day: ship the outlines
        # (mi/scripts/build_mi_gap_outlines.py). So the rule is the plain one
        # again — a `counties` tag is a PROMISE THE PANEL CAN LOCATE THAT
        # COUNTY, and an instance keeps it by shipping the geometry rather than
        # by the gate looking away. An instance with no outlines that tags a
        # gap now fails here and is told which file to build, which is the
        # answer its score was really waiting on.
        for slug in e.get("counties") or []:
            if slug not in outlines:
                problems.append(
                    "%s: county %r has no data/app/%s-county-outline.json — the "
                    "gaps panel fetches that file to decide whether this gap is "
                    "where a reader clicked, so the tag would make it claim a "
                    "clean spot inside a county this gap covers"
                    % (where, slug, slug))
        if e.get(EVERY_COUNTY) is not None:
            if e.get(EVERY_COUNTY) is not True:
                problems.append(
                    "%s: %s must be true or absent, never %r — it is a claim, "
                    "and a false one is the same as not making it"
                    % (where, EVERY_COUNTY, e.get(EVERY_COUNTY)))
            if e.get("counties"):
                problems.append(
                    "%s: %s says this record accounts for every county in the "
                    "state and `counties` names %d of them. Those are different "
                    "claims: drop the tags if the record is statewide, or drop "
                    "%s if it covers only the counties it lists"
                    % (where, EVERY_COUNTY, len(e["counties"]), EVERY_COUNTY))
        problems.extend(ask_problems(where, e))
        problems.extend(counted_prose_problems(where, e))
    return problems


# "In 12 of Wisconsin's 72 counties…" ABOVE A LIST OF ELEVEN. That shipped on
# 2026-09-02 and every gate stayed green, because the gates compare the shipped
# JSON to the guidebook and the two agreed — on a number that was wrong in both.
# A COUNT IN PROSE IS A CLAIM ABOUT THE ARRAY BESIDE IT, and it is the one thing
# an equality check between two copies can never see. The cause was a
# multi-replacement edit whose last assertion failed, so none of the earlier
# replacements were written and nobody re-read the file; the count then went
# stale silently for one release. This makes the prose answer to the data.
# A gap record that states how many counties it covers must state the number it
# LISTS. Three shapes appear in practice and all three are checked, because the
# first pattern here caught only one of them: "In 12 of ..." (the original),
# "... 67 of the 91 this site serves" (a summary written for a reader), and an
# `area` of "67 served counties". The second and third went unchecked, which
# matters most exactly when it is easiest to get wrong — two changes in flight
# each removing one county from the same list, each correctly decrementing the
# count to the same value, and the merge of the two leaving the list one shorter
# than the number above it. The gate turns that silent wrong answer into a
# failed build. `ward-polling-places` deliberately does not match: its area
# counts WARDS and municipalities, not counties.
COUNTED_PROSE = re.compile(r"(?i)\bIn (\d+) of\b|\b(\d+) of the \d+\b"
                           r"|^(\d+) served counties$")


def counted_prose_problems(where, entry):
    """A gap whose summary counts counties must count the ones it lists."""
    counties = entry.get("counties") or []
    if not counties:
        return []                        # a gap with no county list counts nothing
    out = []
    for field in ("summary", "area"):
        said = COUNTED_PROSE.search(str(entry.get(field) or ""))
        if not said:
            continue
        n = int(next(g for g in said.groups() if g))
        if n != len(counties):
            out.append("%s: the %s says %d counties and `counties` lists %d — the "
                       "panel would print a number above a list that contradicts it"
                       % (where, field, n, len(counties)))
    return out


def render(entries):
    out = []
    for e in entries:
        row = {}
        for key in FIELD_ORDER:
            if key == "counties":
                row[key] = list(e.get("counties") or [])
            elif key == "layer":
                row[key] = e.get("layer") or None
            elif key == EVERY_COUNTY:
                # Omitted when absent rather than written false, so adding the
                # field churns no record that does not claim it.
                if e.get(key):
                    row[key] = True
            else:
                row[key] = e[key]
        out.append(row)
    # id order, so a reordered guidebook block does not churn the data file
    out.sort(key=lambda r: r["id"])
    # Keyed BY GAP ID, not wrapped in a list: validate_index.py's roster check
    # measures len() of the top-level object, so a {"gaps": [...]} wrapper would
    # give it a floor of 1 and guard nothing. Keyed, the floor is a real count —
    # and it matches the other keyed payloads (il-county-clerks, municipal-officials).
    return json.dumps({r["id"]: r for r in out}, separators=(",", ":"), ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify the shipped file, write nothing")
    ap.add_argument("--metro", help="emit another fork's key instead of this worksheet's")
    ap.add_argument("--out", help="write somewhere other than this repo's data/app/")
    args = ap.parse_args()
    out_path = args.out or OUT_PATH

    # The guidebook is a fleet-wide document with one array per metro (the
    # coverage-map block's shape), so the fork reads ITS OWN key rather than a
    # hardcoded one — that is what lets the same script run in every fork.
    w = worksheet()
    metro = args.metro or w["this_metro"]

    # --metro AND --out ARE ONE ARGUMENT, and forgetting the second one is the
    # only way this script has ever touched a wrong file. --metro chooses the
    # guidebook BLOCK; --out chooses the FILE, and nothing tied them together.
    # `--metro wisconsin` alone read Wisconsin's gaps and wrote them over
    # ILLINOIS's shipped file, reporting success. Nothing downstream named the
    # cause: build_county_status.py failed on "gap 'aldermanic-incomplete-
    # filings' names unknown county slug 'calumet'" and build_history_page.py
    # on a stale page, both symptoms one step removed — and the pair only fired
    # at all because the two states' slug vocabularies happen to disagree. Two
    # metros that shared a slug would have shipped it.
    #
    # THE --check PATH WAS THE WORSE HALF AND IS WHY THIS GUARD COVERS IT.
    # `--check --metro wisconsin` compares Wisconsin's block against Illinois's
    # FILE, so it reports FAIL on a correct tree — and reports **OK** on a tree
    # where the bad write above has already happened, because then the wrong
    # file really does hold the wrong content. A verification that passes
    # BECAUSE of the defect it should catch is worse than one that writes it,
    # and this one did exactly that on 2026-09-02 before Lincoln shipped. CI
    # always pairs the two flags (smoke-test.yml); it is the hand-run that lies.
    if args.metro and not args.out and metro != w["this_metro"]:
        fail("--metro %s needs --out: --metro picks the guidebook block and --out "
             "picks the file, so without it this %s %s's gaps against %s — this "
             "repo's own %s file. Pass the sibling's path, e.g. --metro %s --out "
             "<tag>/data/app/coverage-gaps.json."
             % (metro, "checks" if args.check else "writes", metro,
                os.path.relpath(OUT_PATH, REPO_ROOT), w["this_metro"], metro))
    gaps = load_gaps()
    entries = gaps.get(metro)
    if entries is None:
        fail("gaps block has no %r array (keys: %s). Add one for this fork, even if "
             "empty, so the absence is deliberate rather than an oversight."
             % (metro, list(gaps)))

    # Layer ids and outline slugs are per-fork. This repo's own metro measures
    # against this repo; a sibling measures against the instance its --out path
    # points into (sibling_surfaces), and only an unrecognizable path skips.
    own = metro == w["this_metro"]
    if own:
        layer_ids, outlines = known_layer_ids(w), shipped_outline_slugs()
    else:
        layer_ids, outlines = sibling_surfaces(out_path)
    # A token resolves BEFORE anything is checked or written, so that every
    # rule below and the shipped bytes read the same text. `authored` is kept
    # only to report each token-bearing field's budget at the end.
    authored = entries
    entries, problems = resolve_all(authored)
    problems.extend(validate(entries, layer_ids, outlines))
    problems.extend(ask_reference_problems(entries))

    # LOCATION AWARENESS IS THE PANEL'S WHOLE POINT, so an instance that ships
    # county outlines and tags no gap with one has a dead "Where you clicked"
    # section and does not know it. That is not hypothetical: Wisconsin shipped
    # exactly that state — ten gaps, every `counties` array empty — and the
    # panel told a reader who had clicked to click. Every other guard passed.
    mappable = sum(1 for e in entries if (e.get("counties") or []))
    if outlines and entries and not mappable:
        problems.append(
            "%s ships %d county outline(s) and not one of its %d gaps names a "
            "county, so the panel can never lead with the gaps that apply where "
            "a reader clicked. Tag the gaps whose area maps to counties."
            % (metro, len(outlines), len(entries)))
    if problems:
        for p in problems:
            print("  %s" % p, file=sys.stderr)
        fail("%d invalid gap entr%s" % (len(problems), "y" if len(problems) == 1 else "ies"))

    payload = render(entries)
    by_kind = {}
    for e in entries:
        by_kind[e["kind"]] = by_kind.get(e["kind"], 0) + 1
    summary = ", ".join("%s %d" % (k, by_kind[k]) for k in sorted(by_kind))

    if args.check:
        if not os.path.exists(out_path):
            fail("data/app/coverage-gaps.json is missing — run this script")
        with open(out_path, encoding="utf-8") as f:
            shipped = f.read()
        if shipped != payload:
            fail("data/app/coverage-gaps.json differs from the guidebook's gaps block "
                 "(%d vs %d bytes). Edit the guidebook, then regenerate."
                 % (len(shipped), len(payload)))
        for line in token_budgets(authored, entries):
            print(line)
        for line in pending_ask_lines(entries):
            print(line)
        print("build-coverage-gaps: OK — shipped file matches the guidebook "
              "(%s: %d gaps, %s; %d mapped to counties)"
              % (metro, len(entries), summary, mappable))
        return

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(payload)
    for line in token_budgets(authored, entries):
        print(line)
    for line in pending_ask_lines(entries):
        print(line)
    print("build-coverage-gaps: wrote %s — %s: %d gaps (%s), %d mapped to "
          "counties, %d bytes"
          % (os.path.relpath(out_path, REPO_ROOT), metro, len(entries), summary,
             mappable, len(payload)))


if __name__ == "__main__":
    main()
