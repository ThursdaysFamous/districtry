#!/usr/bin/env python3
"""
Docs gate: a layer count written in prose must equal the layer count shipped.

WHY THIS EXISTS. "N layers" is the fleet's most-repeated number and its least
watched. It appears 28 times across this repo, and NOTHING compared any of them
against a worksheet until this gate — which is the failure shape the Michigan
go-live named three times over: a claim nothing measures against the thing it
claims. Two gates already cover the ADJACENT questions and neither covers this
one. build_landing_page.py emits the root page's six `aria-label="…, N layers"`
strings from `len(worksheet["layers"])`, so those are generated and drift-gated
already (they are excluded below for exactly that reason). fleet_status.py
diffs each instance's layer IDS against the guidebook's coverage matrix, weekly
and WARN-only — a set comparison that says nothing about a number typed into a
sentence somewhere else in the same document.

WHAT IT FOUND ON INTRODUCTION (2026-09-04), all four wrong the day they were
written or the day an instance grew past them:

  * docs/press-list.json x2 — Iowa "19 layers" in the pitch angle and in the
    Des Moines AP bureau row. Iowa ships 20. This is the outbound press list:
    the number a journalist would have been handed.
  * docs/PRESS_LIST.md — the same claim, carried through by the generator.
  * docs/WI_PHASE2_PLAN.md — "Wisconsin ships 19 layers" in the stub whose
    whole job is to say the shipped state supersedes the plan. Wisconsin's
    worksheet held 31 the day that line was written; it was never right.

WHAT IS CANONICAL. Each instance's own `metro-worksheet.json`, discovered from
the TREE the way validate_instance_registration.py discovers instances — a
top-level directory carrying both an index.html and a data/app/. Illinois's
worksheet stayed at the repo root when R2.3 moved its app into `il/`, so the
path is probed rather than assumed (the check_cache_version.py rule).

FIVE PATTERNS, because the claim is written five ways. (This heading said TWO
while listing three; D and E were added 2026-09-21.)

  A. A count next to one instance name — "the Iowa half (all 99 counties, 19
     layers)", "### Wisconsin — 31 layers", "**39 layers** ship in Illinois
     today". Matched by finding `N layers` and taking the NEAREST instance
     name on EITHER side, by character distance. Both halves are load-bearing
     and each was learned from a false positive this gate produced on its own
     first run. Nearest, because "Illinois reached 91 counties; Wisconsin
     reached 31 layers" and "NYC, SF, and Wisconsin (31 layers…)" each name an
     earlier instance the number does not belong to. Either side, because
     README.md's "**39 layers** ship in Illinois today" puts the name AFTER,
     and reading only backwards attributed Illinois's 39 to a Michigan
     mentioned in the previous sentence.

  B. Name-and-number pairs on a line that also says "layers" — the guidebook's
     "Fleet totals: Chicago 39 · NYC 27 · SF 16 · Wisconsin 31 · Iowa 20 ·
     Michigan 5 layers", where six counts share ONE "layers" token. Pattern A
     sees only Michigan there. Two guards keep it off ordinary prose: a pair
     counts only when the number is followed by a separator or by "layers"
     itself (so "Illinois reached 91 counties" is skipped), and the LINE must
     pair at least MIN_TOTALS_PAIRS distinct instances, which is the shape of
     a totals line and of nothing else.

     That threshold exists because of a real collision, not a hypothetical
     one: Wisconsin has a county named IOWA, and the guidebook's Wisconsin
     supervisor-gap record lists per-county seat counts — "Green Lake 19,
     Iowa 21, Kenosha 23, La Crosse 30" — where `Iowa 21` is Iowa County's
     twenty-one supervisors and reads exactly like a claim that the Iowa
     instance ships 21 layers. An instance name that is also a county name
     somewhere else in the fleet is permanent, so the discriminator has to be
     structural.

  C. A count written the other way round, "N for <instance>" with the noun
     ahead of it — README.md's "every declared layer id is still registered
     (39 for Illinois)". Neither A nor B sees it: A wants the word `layers`
     beside the number, and B wants the NAME first. That sentence was stale
     from the day the `ssa` layer landed and this gate read it as nothing.

     THE BARE SHAPE CANNOT BE THE RULE, and that is measured rather than
     cautious. `\d+ for <instance>` occurs five times in the scanned surface
     and only ONE is a layer count. The other four are a different noun
     entirely: docs/DEV_PROCESS_ASSESSMENT.md's "59 colours for Illinois, 37
     for NYC, 23 for SF" counts dark-mode map COLOURS derived from layers (and
     that line contains the word "layers", so a line-level guard would not
     save it), and the press list's "Day 9 for NYC and San Francisco" is a
     DAY. Matching the bare shape would fail the build on four correct
     sentences.

     The discriminator is that a layer count is THE FIRST NUMBER AFTER THE
     WORD "layer" on its line. In the README the span between `layer` and
     `39` holds no other number; in the colours line it holds `59`, whose own
     noun is `colours`. An intervening number is allowed only when it is
     itself an `N for <instance>` pair, so "(39 for Illinois, 27 for NYC)"
     reports both while the colours list reports neither. The cost is stated
     rather than hidden: a second instance's count in a span that also carries
     a non-pair number is not read, and the first claim on the line failing is
     what brings a human to it.

  D. A count with the instance name BETWEEN it and the noun — the press list's
     "one free open-source lookup covering all 27 NYC layers". Pattern A wants
     the number immediately before "layers" and never matches, so the nearest-
     name search never runs and the claim is dropped WHOLE rather than
     misattributed. That claim was invisible to this gate from the day the gate
     was written, in the outbound press list, which is the one file whose
     docstring above already calls out as "the number a journalist would have
     been handed". No nearest-name logic applies: the name is in the phrase.

  E. A bare "N layers" on a line that also names an instance's own WORKSHEET —
     "27 layers in `ny/metro-worksheet.json`". A worksheet path names exactly
     one instance and can mean nothing else, which is the structural
     discriminator pattern B already demands.

     THE OBVIOUS FIX WAS MEASURED AND REJECTED. The claim that prompted this
     has "New York City" 78 characters back, across a hard line wrap, just
     outside LOOKBACK's 60-character window — so raising LOOKBACK looks like
     the fix. It is not. Measured across the scanned surface: 60 reads 28
     claims with 2 mismatches; 90 finds this one and ALSO invents "Iowa 4" and
     "Chicago 132", neither a layer count; 120 adds "SF 12" and a stale
     "Chicago 39"; 200 adds "Wisconsin 11" and "Iowa 132". Nine mismatches
     bought for two real ones. The window is well chosen and is left alone.

WHAT IT DOES NOT SCAN. `docs/archive/` (preserved verbatim by convention — the
whole point is that it is not maintained), scripts and tests (a "Thread-5
layers" in a smoke test is a thread name, not a count), and the generated root
landing page. A doc it does not scan is a doc where this number is unwatched;
widen the surface rather than exempting a file.

HISTORICAL_COUNTS is for a past-tense claim that was true when written and has
since been overtaken — "SF had 16 layers carrying zero sources" is fine today
because SF still ships 16, and stops being fine the day SF ships a 17th. It is
EMPTY on introduction, which is a measurement rather than an omission: every
past-tense count in the tree happens to match today. Each entry carries its
reason and date and is re-audited every run, so an entry that stops matching
anything FAILS as orphaned rather than sitting there excusing nothing — the
property ACCEPTED_DROPS, EXPECTED_UNREACHABLE and ACCEPTED_SHORTFALLS have.

Usage:
    python3 scripts/validate_doc_counts.py
    python3 scripts/validate_doc_counts.py --report   # print every claim found
    python3 scripts/validate_doc_counts.py --selftest # pattern C's guard, no files read
"""

import argparse
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Every name any document uses for an instance, longest first so "New York
# City" wins over "New York" and the tag it maps to is unambiguous.
INSTANCE_NAMES = {
    "San Francisco": "ca",
    "New York City": "ny",
    "California": "ca",
    "New York": "ny",
    "Chicago": "il",
    "Illinois": "il",
    "Wisconsin": "wi",
    "Michigan": "mi",
    "Iowa": "ia",
    "NYC": "ny",
    "SF": "ca",
}

# A past-tense count that was true when written and has since been overtaken.
# Entries: {"path", "name", "count", "reason", "recorded"}. See the docstring —
# empty is the measured state, not an unfinished table.
HISTORICAL_COUNTS = [
    # 2026-09-21, when patterns D and E made two long-invisible claims readable.
    # The plan's Context section records the state of `ny/` BEFORE the plan ran
    # and says so in its own heading. It was TRUE when written: the worksheet
    # held 27 layers when it was read on 2026-09-18 and PR 2 took it to 33
    # later the SAME DAY. Correcting the number to 33 would make the plan's
    # starting state a state that never preceded the plan, so the section was
    # put into the past tense instead and the figure left as the reading it is.
    {"path": "docs/NY_EXPANSION_PLAN.md", "name": "New York", "count": 27,
     "reason": "Dated pre-expansion reading: ny/metro-worksheet.json held 27 layers "
               "when the plan was written on 2026-09-18, and PR 2 took it to 33 the "
               "same day. The section is marked past tense rather than renumbered",
     "recorded": "2026-09-21"},
    # The FIRST entry, 2026-09-12, when the `ssa` layer took Illinois 39 -> 40.
    # This sentence is a DATED MEASUREMENT, not a live claim: it reports how many
    # layers a Will or DuPage point resolved when the coverage-wash problem was
    # diagnosed, and its three figures (17-21, 32, 25) were measured together
    # against that same 39. Bumping only the denominator would leave a ratio
    # nobody ever measured, which is worse than a stale number that says what it
    # meant on its day — the same posture the county cards' dated rows take.
    {"path": "docs/EXPANSION_GUIDE.md", "name": "Chicago", "count": 39,
     "reason": "Dated measurement of the coverage-wash diagnosis: a Will or DuPage "
               "point resolved 17-21 of the then-39 layers against Chicago's 32 and "
               "suburban Cook's 25. All three figures were measured together, so the "
               "39 cannot be updated alone.",
     "recorded": "2026-09-12"},
    # 2026-09-18, when the New York instance grew its first statewide layers and
    # went 27 -> 31. This sentence RECORDS WHAT SHIPPED ON ITS DAY: it says NYC's
    # sources page followed San Francisco's "once its 27 layers had been through
    # the same extraction", and names the three matrices built then as 39, 27 and
    # 16 rows. All three figures were counted together at that moment, so raising
    # the 27 alone would leave a row count nobody ever built, and raising all
    # three would claim a change that had not happened yet when the sentence was
    # written. A past-tense record is left as it was.
    {"path": "docs/DEV_PROCESS_ASSESSMENT.md", "name": "NYC", "count": 27,
     "reason": "Dated record of the sources-page extraction: NYC's page was built "
               "from its then-27 layers, alongside matrices of 39 and 16 rows for "
               "Illinois and San Francisco, all counted in that one change.",
     "recorded": "2026-09-18"},
]

# How far to look either side of a bare "N layers" for the instance it belongs
# to. Back far enough for "the natural byline for the Iowa half (all 99
# counties, 19 layers)"; forward far enough for "**39 layers** ship in
# Illinois today"; short enough either way that a name a sentence off never
# claims a number it does not own.
LOOKBACK = 60
LOOKAHEAD = 30

# How many distinct instances a line must pair with a number before pattern B
# reads it as a fleet-totals line. Three separates the totals line (six) from
# every per-county list in the tree (one, and the collision is Iowa County WI).
MIN_TOTALS_PAIRS = 3

# A claim MEASURED WRONG in a file this project does not edit. Deliberately NOT
# folded into HISTORICAL_COUNTS, whose entries mean "was true when written" — a
# wrong claim filed under that name would make the list itself lie, which is the
# failure this whole gate exists to catch. Same contract as ACCEPTED_DROPS and
# EXPECTED_UNREACHABLE otherwise: a reason, a date, printed EVERY run so it
# cannot go quiet, and a FAIL when it is orphaned or when the claim is fixed.
#
# An entry here is a debt, not an exemption. It says the number is wrong, the
# owner has been told, and this project is not the one to change it.
OWNER_HELD_COUNTS = [
    # docs/press-list.json is the outbound press list and is the operator's
    # file; this session flags it and does not edit it. The claim sits in the
    # `angle` for City & State New York, wave 4, which carries no `sent` key —
    # so it is UNSENT, and 27 is the number a journalist would be handed for an
    # app that ships 33. It reaches no reader through docs/PRESS_LIST.md, which
    # does not render the `angle` field.
    {"path": "docs/press-list.json", "name": "NYC", "count": 27,
     "reason": "Unsent wave-4 pitch (City & State New York) understating the app at 27 "
               "layers; ships 33. The press list is the operator's file — flagged on "
               "ny/BOARD.md, not edited here",
     "recorded": "2026-09-21"},
]

COUNT_RE = re.compile(r"\b(\d{1,3})\s+layers?\b")
NAME_RE = re.compile(r"\b(" + "|".join(re.escape(n) for n in INSTANCE_NAMES) + r")\b")
# Pattern B: a name, a number, then a separator or the word "layers" — never
# another noun, which is what keeps "Illinois reached 91 counties" out.
PAIR_RE = re.compile(
    r"\b(" + "|".join(re.escape(n) for n in INSTANCE_NAMES) + r")\b"
    r"[\s:—–-]*\**\s*(\d{1,3})\s*\**\s*(?=$|[·,;)]|\band\b|layers?\b)"
)
# Pattern C: "N for <instance>", where the noun sits ahead of the number. The
# guard is in _for_pair_claims, not here — see the docstring's pattern C.
FOR_PAIR_RE = re.compile(
    r"\b(\d{1,3})\s+for\s+\**("
    + "|".join(re.escape(n) for n in INSTANCE_NAMES) + r")\b"
)
# Pattern D: "N <instance> layers", the name sitting BETWEEN the number and
# the noun. COUNT_RE cannot see it — it wants the number immediately before
# "layers" — and the nearest-name search never runs, so the claim is dropped
# whole. The press list's "all 27 NYC layers" went unread by this gate from the
# day the gate was written. No nearest-name logic is needed or wanted here: the
# name is IN the phrase, so the attribution is unambiguous.
COUNT_NAMED_RE = re.compile(
    r"\b(\d{1,3})\s+(" + "|".join(re.escape(n) for n in INSTANCE_NAMES)
    + r")\s+layers?\b")
# Pattern E: a bare "N layers" on a line that also names an instance's own
# WORKSHEET. A worksheet path names exactly one instance and cannot mean
# anything else, which is the structural discriminator this gate's docstring
# already demands of pattern B.
#
# WIDENING LOOKBACK WAS MEASURED AND REJECTED, and the numbers are the reason
# this rule exists instead. The claim that prompted it — NY_EXPANSION_PLAN.md's
# "27 layers in `ny/metro-worksheet.json`" — has "New York City" 78 characters
# back, across a hard line wrap, just outside the 60-character window. Raising
# LOOKBACK to 90 does find it and ALSO invents two claims that are not layer
# counts ("Iowa 4", "Chicago 132"); 120 adds "SF 12" and a stale "Chicago 39";
# 200 adds "Wisconsin 11" and "Iowa 132". Nine mismatches against two real
# ones. The window is well chosen and is left alone.
WORKSHEET_PATH_RE = re.compile(r"\b([a-z]{2})/metro-worksheet\.json\b")
# Display label only — attribution is by TAG. Kept explicit because "New York
# City" and "New York" both map to `ny` and the output should not wobble.
CANONICAL_NAME = {"il": "Chicago", "ny": "New York", "ca": "San Francisco",
                  "wi": "Wisconsin", "ia": "Iowa", "mi": "Michigan"}
LAYER_WORD_RE = re.compile(r"\blayers?\b", re.IGNORECASE)
ANY_NUMBER_RE = re.compile(r"\d+")


def instances():
    """tag -> (worksheet path, shipped layer count), discovered from the tree."""
    found = {}
    for name in sorted(os.listdir(REPO_ROOT)):
        d = os.path.join(REPO_ROOT, name)
        if not os.path.isdir(d) or name.startswith("."):
            continue
        if not (os.path.isfile(os.path.join(d, "index.html"))
                and os.path.isdir(os.path.join(d, "data", "app"))):
            continue
        # Illinois's worksheet stayed at the root when R2.3 moved its app down.
        rel = os.path.join(name, "metro-worksheet.json")
        if not os.path.isfile(os.path.join(REPO_ROOT, rel)):
            rel = "metro-worksheet.json"
        try:
            with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
                sheet = json.load(fh)
        except (OSError, ValueError):
            continue
        found[name] = (rel, len(sheet.get("layers") or []))
    return found


def documents():
    """Every prose document whose layer counts this gate watches."""
    out = []
    for rel in ("README.md", "CLAUDE.md", "WATCH.md"):
        if os.path.isfile(os.path.join(REPO_ROOT, rel)):
            out.append(rel)
    for tag in instances():
        for base in ("README.md", "CLAUDE.md", "WATCH.md"):
            rel = os.path.join(tag, base)
            if os.path.isfile(os.path.join(REPO_ROOT, rel)):
                out.append(rel)
    docs = os.path.join(REPO_ROOT, "docs")
    for root, dirs, files in os.walk(docs):
        # docs/archive/ is preserved verbatim; not maintaining it is the point.
        dirs[:] = [d for d in dirs if d != "archive"]
        for f in sorted(files):
            if f.endswith((".md", ".json")):
                out.append(os.path.relpath(os.path.join(root, f), REPO_ROOT))
    return sorted(set(out))


def claims(rel):
    """Every (line, instance name, stated count) this document asserts."""
    try:
        with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return []
    seen, out = set(), []

    def add(pos, name, count):
        line = text.count("\n", 0, pos) + 1
        key = (line, name, count)
        if key not in seen:
            seen.add(key)
            out.append((line, name, count, text[max(0, pos - 70):pos + 40]
                        .replace("\n", " ").strip()))

    # A: the nearest instance name on EITHER side of a bare "N layers".
    for m in COUNT_RE.finditer(text):
        name = _nearest_name(text, m.start(), m.end())
        if name:
            add(m.start(), name, int(m.group(1)))

    # B: name/number pairs on a line that also says "layers" AND pairs enough
    # distinct instances to be a totals line rather than a per-county list.
    for line_text, offset in _lines_with(text, "layer"):
        pairs = list(PAIR_RE.finditer(line_text))
        if len({m.group(1) for m in pairs}) < MIN_TOTALS_PAIRS:
            continue
        for m in pairs:
            add(offset + m.start(), m.group(1), int(m.group(2)))

    # C: "N for <instance>", counted only where N is the first number after the
    # word "layer" on its line.
    for pos, name, count in _for_pair_claims(text):
        add(pos, name, count)

    # D: "N <instance> layers" — the name between the number and the noun.
    for m in COUNT_NAMED_RE.finditer(text):
        add(m.start(), m.group(2), int(m.group(1)))

    # E: a bare "N layers" on a line naming an instance's own worksheet.
    for line_text, offset in _lines_with(text, "metro-worksheet.json"):
        pm = WORKSHEET_PATH_RE.search(line_text)
        if not pm:
            continue
        name = CANONICAL_NAME.get(pm.group(1))
        if not name:
            continue
        for m in COUNT_RE.finditer(line_text):
            add(offset + m.start(), name, int(m.group(1)))
    return out


def _for_pair_claims(text):
    """Every "N for <instance>" that is a LAYER count -> (pos, name, count).

    A layer count is the first number after the word "layer" on its line. An
    intervening number disqualifies it — that is what separates README.md's
    "layer id is still registered (39 for Illinois)" from
    DEV_PROCESS_ASSESSMENT.md's "59 colours for Illinois, 37 for NYC" — unless
    the intervening number is itself an "N for <instance>" pair, so a list of
    genuine per-instance layer counts still reports every entry.
    """
    out = []
    for line_text, offset in _lines_with(text, "layer"):
        layer_words = [m.end() for m in LAYER_WORD_RE.finditer(line_text)]
        if not layer_words:
            continue  # "layer" only as part of a longer word
        pair_spans = [m.span(1) for m in FOR_PAIR_RE.finditer(line_text)]
        for m in FOR_PAIR_RE.finditer(line_text):
            before = [e for e in layer_words if e <= m.start(1)]
            if not before:
                continue  # the number precedes every "layer" word on the line
            span = line_text[max(before):m.start(1)]
            span_start = max(before)
            intruder = False
            for num in ANY_NUMBER_RE.finditer(span):
                abs_start = span_start + num.start()
                if not any(a <= abs_start < b for a, b in pair_spans):
                    intruder = True
                    break
            if intruder:
                continue
            out.append((offset + m.start(), m.group(2), int(m.group(1))))
    return out


def _nearest_name(text, start, end):
    """The instance name closest to a count, looking both ways.

    Distance is measured to the nearer edge of the count, so a name that
    follows it ("39 layers ship in Illinois") can beat one that precedes it
    from further away ("Michigan is the newest." two clauses back).
    """
    best, best_dist = None, None
    for m in NAME_RE.finditer(text[max(0, start - LOOKBACK):start]):
        dist = start - (max(0, start - LOOKBACK) + m.end())
        if best_dist is None or dist < best_dist:
            best, best_dist = m.group(1), dist
    for m in NAME_RE.finditer(text[end:end + LOOKAHEAD]):
        dist = m.start()
        if best_dist is None or dist < best_dist:
            best, best_dist = m.group(1), dist
    return best


def _lines_with(text, needle):
    pos = 0
    for line in text.split("\n"):
        if needle in line:
            yield line, pos
        pos += len(line) + 1


# --- self-test ----------------------------------------------------------------
#
# Pattern C's guard is the whole of pattern C: the bare `N for <instance>` shape
# occurs five times in the scanned surface and only ONE is a layer count. The
# other four are correct English sentences about something else, so a loosened
# pattern fails the build on them — and nothing about a green run says the guard
# still holds, because the four are only visible when the pattern is wrong.
# These are the five real lines plus the list case the allowance exists for.
# Stdlib only, no network, no files read.
_C_CASES = [
    ("README.md's real claim",
     "the inline script passes `node --check`, every declared layer id is still "
     "registered (40 for Illinois), no dataset is embedded inline",
     [("Illinois", 40)]),
    # docs/DEV_PROCESS_ASSESSMENT.md. Dark-mode map COLOURS derived from layers,
    # not layer counts — and the line carries the word "layers", so a
    # line-level guard does not save it. NYC ships 27, SF 16.
    ("dark-mode colours, on a line that says 'layers'",
     "each derives from its OWN layers: 59 colours for Illinois, 37 for NYC, "
     "23 for SF. **(3) SF's smoke test",
     []),
    # docs/press-list.json and the PRESS_LIST.md it generates: a DAY number.
    ("the press list's 'Day 9 for NYC'",
     "Day 8 (the Tuesday after the holiday-shortened week) for Wisconsin and "
     "Iowa; Day 9 for NYC and San Francisco. 6:30-8:00am",
     []),
    ("a genuine two-instance list — why an intervening PAIR is allowed",
     "every declared layer id is still registered (40 for Illinois, 27 for NYC)",
     [("Illinois", 40), ("NYC", 27)]),
    ("no 'layer' word on the line",
     "we shipped 12 for Illinois and 9 for Iowa that week",
     []),
    ("the number precedes the only 'layer' word",
     "40 for Illinois is what the layer registry reports",
     []),
]


# Pattern D reads a name that sits BETWEEN the number and the noun, and must
# not read the shapes A and B already own (which would double-report) or the
# ones that are not layer counts at all.
_D_CASES = [
    ("the press list's real claim",
     "one free open-source lookup covering all 27 NYC layers, built outside government",
     [("NYC", 27)]),
    ("a full instance name in the same shape",
     "the 16 San Francisco layers each carry a source row",
     [("San Francisco", 16)]),
    ("pattern A's shape is NOT pattern D's — no name between",
     "New York ships 33 layers today",
     []),
    ("a number, a name, and a different noun",
     "we wrote 27 NYC pitches that week",
     []),
    ("a name that is not an instance",
     "all 27 Brooklyn layers",
     []),
]

# Pattern E attributes a bare "N layers" by the WORKSHEET PATH on its own line.
# A worksheet path names exactly one instance; nothing else on the line is
# consulted, which is what makes it safe where widening LOOKBACK was not.
_E_CASES = [
    ("the plan's real claim",
     "with 27 layers in `ny/metro-worksheet.json` (read 2026-09-18). Measured on that date:",
     [("New York", 27)]),
    ("the Wisconsin stub's real claim",
     "Wisconsin ships 31 layers (`wi/metro-worksheet.json`)",
     [("Wisconsin", 31)]),
    ("a worksheet path with no count on the line",
     "the list that drives it is `ia/metro-worksheet.json`",
     []),
    ("a count with no worksheet path on the line",
     "27 layers were built that week",
     []),
    ("an unknown tag in the path",
     "42 layers in `zz/metro-worksheet.json`",
     []),
]


def _selftest():
    bad = 0
    for label, line, expect in _C_CASES:
        got = [(n, c) for _, n, c in _for_pair_claims(line + "\n")]
        if got != expect:
            bad += 1
            print("  BAD pattern C: %s\n      got %s, expected %s"
                  % (label, got, expect), file=sys.stderr)
    for label, line, expect in _D_CASES:
        got = [(m.group(2), int(m.group(1))) for m in COUNT_NAMED_RE.finditer(line)]
        if got != expect:
            bad += 1
            print("  BAD pattern D: %s\n      got %s, expected %s"
                  % (label, got, expect), file=sys.stderr)
    for label, line, expect in _E_CASES:
        pm = WORKSHEET_PATH_RE.search(line)
        name = CANONICAL_NAME.get(pm.group(1)) if pm else None
        got = ([(name, int(m.group(1))) for m in COUNT_RE.finditer(line)]
               if name else [])
        if got != expect:
            bad += 1
            print("  BAD pattern E: %s\n      got %s, expected %s"
                  % (label, got, expect), file=sys.stderr)
    total = len(_C_CASES) + len(_D_CASES) + len(_E_CASES)
    if bad:
        print("validate-doc-counts selftest: FAIL — %d of %d case(s) wrong"
              % (bad, total), file=sys.stderr)
        return 1
    print("validate-doc-counts selftest: OK — %d cases. Pattern C reads the one "
          "real 'N for <instance>' count and none of the four sentences sharing "
          "its shape; D reads a name between the number and the noun without "
          "taking A's shape; E attributes by worksheet path alone." % total)
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", action="store_true",
                    help="print every layer-count claim found, not just failures")
    ap.add_argument("--selftest", action="store_true",
                    help="run pattern C against the shapes it must and must not read")
    args = ap.parse_args()

    if args.selftest:
        return _selftest()

    shipped = instances()
    if len(shipped) < 2:
        print("validate-doc-counts: FAIL — found %d instance(s); the tree scan "
              "is broken" % len(shipped), file=sys.stderr)
        return 1

    problems, checked, matched_exemptions = [], 0, set()
    matched_held = set()
    for rel in documents():
        for line, name, stated, context in claims(rel):
            tag = INSTANCE_NAMES[name]
            if tag not in shipped:
                continue
            sheet, actual = shipped[tag]
            checked += 1
            if args.report:
                mark = "ok " if stated == actual else "BAD"
                print("  %s %s:%d  %s %d (ships %d)"
                      % (mark, rel, line, name, stated, actual))
            if stated == actual:
                continue
            held = next((i for i, e in enumerate(OWNER_HELD_COUNTS)
                         if e["path"] == rel and e["name"] == name
                         and e["count"] == stated), None)
            if held is not None:
                matched_held.add(held)
                print("  owner-held: %s:%d says %s %d, ships %d — %s (%s)"
                      % (rel, line, name, stated, actual,
                         OWNER_HELD_COUNTS[held]["reason"],
                         OWNER_HELD_COUNTS[held]["recorded"]))
                continue
            excuse = next((i for i, e in enumerate(HISTORICAL_COUNTS)
                           if e["path"] == rel and e["name"] == name
                           and e["count"] == stated), None)
            if excuse is not None:
                matched_exemptions.add(excuse)
                print("  historical: %s:%d says %s %d, ships %d — %s (%s)"
                      % (rel, line, name, stated, actual,
                         HISTORICAL_COUNTS[excuse]["reason"],
                         HISTORICAL_COUNTS[excuse]["recorded"]))
                continue
            problems.append(
                "  %s:%d — says %s ships %d layers; %s lists %d\n"
                "      …%s…" % (rel, line, name, stated, sheet, actual, context))

    for i, entry in enumerate(OWNER_HELD_COUNTS):
        if i not in matched_held:
            problems.append(
                "  OWNER_HELD_COUNTS entry %d is orphaned — nothing in %s now "
                "claims %s %d. If the owner fixed it, delete the entry."
                % (i, entry["path"], entry["name"], entry["count"]))
    for i, entry in enumerate(HISTORICAL_COUNTS):
        if i not in matched_exemptions:
            problems.append(
                "  HISTORICAL_COUNTS entry %d is orphaned — nothing in %s now "
                "claims %s %d. Delete the entry."
                % (i, entry["path"], entry["name"], entry["count"]))

    if problems:
        print("validate-doc-counts: FAIL — a document states a layer count the "
              "worksheet contradicts\n" + "\n".join(problems), file=sys.stderr)
        print("\n  Fix the DOCUMENT, not the worksheet. A generated document "
              "(docs/PRESS_LIST.md) is fixed at its source (docs/press-list.json) "
              "and regenerated.", file=sys.stderr)
        return 1

    print("validate-doc-counts: OK — %d layer-count claim(s) across %d document(s) "
          "agree with %d worksheet(s)"
          % (checked, len(documents()), len(shipped)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
