#!/usr/bin/env python3
"""
ISBE's precinct-level results archive, read as a RE-PRECINCTING TRIPWIRE.

WHY THIS EXISTS. Most of this project's county precinct layers are built from
Census 2020 voting districts, which are a snapshot: the moment a county
consolidates, splits or renames a precinct, the shipped fabric is silently
wrong and nothing notices. docs/EXPANSION_GUIDE.md §2.5.1 step 6 asks for a
check on exactly that, and until now it could only be run where a results
vendor happened to carry the county — 34 counties on one vendor, 13 on
another, 17 on a third.

ISBE carries all 102, from one host, back to 1998:

    https://www.elections.il.gov/Downloads/ElectionOperations/ElectionResults/
        ByOffice/<electionId>/<electionId>-<officeCode>-<OFFICE>-<tag>.csv

The filenames are DISCOVERED from ElectionVoteTotals.aspx rather than guessed —
that page links every office's CSV for a chosen election, and the office code
and tag are not derivable from the election id.

HOW THE COMPARISON IS MADE, and why it is election-to-election rather than
against the shipped layer. The obvious check — diff ISBE's precinct names for a
county against the names in that county's shipped file — was tried first and is
WRONG. On the 2026 General Primary it agrees exactly for 20 of the 33 counties
that ship a precinct layer and disagrees for 13, and the disagreements are not
drift: Richland reports 30 names against 21 shipped precincts, which is the NINE
sub-precinct reporting units its own gap record already documents. A county may
report a precinct in parts, and that is a fact about ISBE's reporting units, not
about the fabric having moved.

Comparing one election to another is immune to all of it. Whatever convention a
county reports under, it reports under the same one in both files, so a name set
that CHANGES is the county having changed something. That is the check the
guidebook asked for.

TWO NORMALISATIONS, BOTH MEASURED. Federal/UOCAVA reporting units are dropped:
McDonough reports BETHEL-1 beside BETHEL-F15, one real precinct and one
ballot class, and 873 such names exist statewide. The rule matches `-F<digits>`
and `-FED<digits>` ONLY, and that precision is load-bearing — a rule that
stripped any trailing `-TOKEN` would eat Calhoun's HARDIN-GILEAD and
BELLEVIEW-HAMBURG, which are merged precincts whose names really do end that
way. Comparison is otherwise case- and whitespace-normalised, because ISBE's
own capitalisation drifts between elections ("McDONOUGH" / "MCDONOUGH").

WHAT THE ARCHIVE DOES NOT COVER, measured 2026-09-03 rather than assumed:
CONSOLIDATED ELECTIONS carry no by-office CSV at all. Ids 68 (2025), 64 (2023)
and 59 (2021) each link zero files, while every general and every primary links
18-23. So this reads the November and March ballots and cannot see the April
ones — which matters because a county that re-precincts for a municipal
election shows up here only at the next general. `--list` says which elections
have files, so that is visible before a comparison rather than as a failure
part-way through one.

THE CAVEAT TO CARRY INTO ANY BUILDER THAT USES THIS: the archive's
`Registration` column is self-reported and is sometimes 0 — Calhoun 2026, all
of Brown 2020 — so a floor keyed on it fires on the publisher's blank rather
than on a real loss. Nothing here reads it.

Usage:
    python3 scripts/isbe_precinct_fabric.py --list
    python3 scripts/isbe_precinct_fabric.py --compare 66 69
    python3 scripts/isbe_precinct_fabric.py --compare 62 66 --county CALHOUN
"""

import argparse
import collections
import csv
import io
import os
import re
import sys
import glob
import json
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scraper_common import UA_HINTS_CHROME_126, make_fail, require_robots_allowed  # noqa: E402

BASE = "https://www.elections.il.gov"
TOTALS = BASE + "/ElectionOperations/ElectionVoteTotals.aspx"
# BALLOT CLASSES, NOT PRECINCTS. ISBE reports several ballot classes as if they
# were precincts, and counting them makes a county look re-precincted every time
# the ballot changes: on the first statewide run, the 2024 General's
# "PRESIDENTIAL ONLY BALLOT" row simply does not exist in 2026, which read as a
# lost precinct in 30-odd counties at once. That is the cry-wolf failure this
# tripwire would die of.
#
# The vocabulary was MEASURED across both elections rather than guessed — 130
# such names in three families:
#   -F12, -FED01, FEDERAL-F03   a UOCAVA class reported beside its precinct
#   PE01 FED ONLY, FED ONLY 16TH DEM, KI01 16TH FED ONLY
#   PRESIDENT ONLY, PRESIDENTIAL BALLOT ONLY, PRESIDENTIAL ONLY BALLOT
#
# Each pattern is deliberately narrow. `-(F|FED)\d+` matches digits after the
# dash and nothing else, because Calhoun's HARDIN-GILEAD and BELLEVIEW-HAMBURG
# are merged precincts whose real names end in `-<letters>`; and "ONLY" is only
# ever read as a ballot class when FED or PRESIDENT stands beside it.
FEDERAL_ONLY = re.compile(r"-(?:F|FED)\d+$", re.I)
BALLOT_CLASS = re.compile(r"\bFED\s+ONLY\b|\bPRESIDENT(?:IAL)?\b.*\bONLY\b", re.I)


def is_ballot_class(name):
    """True for a reporting unit that is a ballot type rather than a place."""
    return bool(FEDERAL_ONLY.search(name) or BALLOT_CLASS.search(name))


# THE TRAILING `-<digits>` IS A REPORTING ID, NOT PART OF THE PRECINCT'S NAME,
# and reading it as one is what made the first version of this check report four
# counties as having gained precincts when none had.
#
# The tell is that the id REPEATS across different precincts and CHANGES between
# elections. Cass's 2026 primary carries `-002` on six different precincts —
# Ashland 20, Ashland 21, Chandlerville 18, Newmansville 19, Panther Creek 17 and
# Philadelphia 16 — which is a polling place shared by six precincts, not a
# precinct number. And Chandlerville appears twice, as `CHANDLERVILLE 18-002` and
# `CHANDLERVILLE 18-012`: one precinct reported at two ids, which the raw
# comparison counted as two precincts and called Cass 21 -> 23.
#
# A PRECINCT'S OWN NUMBER IS SPACE-SEPARATED and survives: `BEARDSTOWN 5-004`
# strips to `BEARDSTOWN 5`, `GOREVILLE 1-1` to `GOREVILLE 1`, `WINCHESTER III-9`
# to `WINCHESTER III`. So a county that genuinely adds a precinct still shows a
# new name here; only the id collapses.
#
# MEASURED against the 33 counties whose precincts this app ships, 2026 primary:
# exact name-set agreement goes from 12/33 raw to 21/33 stripped, and NOT ONE
# county that agreed raw stops agreeing — the rule strictly improves
# reconciliation rather than trading one error for another. All four counties the
# first run wrongly flagged (Cass, Greene, Johnson, Scott) reconcile on count,
# three of them on names exactly.
#
# It leaves Calhoun alone, which is the check that matters most: neither its 2022
# nor its 2024 names carry a trailing `-<digits>`, so the 7-to-5 merge this script
# is validated against still reads exactly as it did.
REPORTING_ID = re.compile(r"-\d+$")


def precinct_key(name):
    """The precinct's own name, with any trailing reporting id removed."""
    return REPORTING_ID.sub("", name).strip()

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

fail = make_fail("isbe-precinct-fabric")


def _get(url, timeout=180):
    req = urllib.request.Request(url, headers=UA_HINTS_CHROME_126)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def elections():
    """[(id, label)] from the results page's own election dropdown."""
    html = _get(TOTALS, timeout=60).decode("utf-8", "replace")
    m = re.search(r'<select[^>]*ddlElections[^>]*>(.*?)</select>', html, re.S | re.I)
    if not m:
        fail("no election dropdown on %s — the page's structure changed" % TOTALS)
    return re.findall(r'<option[^>]*value="(\d+)"[^>]*>([^<]*)</option>', m.group(1))


# Offices elected by the WHOLE STATE, so their results file carries every
# election authority. A congressional or judicial file covers only part of the
# state, and comparing two elections through one would silently compare a
# subset. Ordered by how reliably each appears on a ballot.
STATEWIDE_OFFICES = (
    "PRESIDENT AND VICE PRESIDENT", "PRESIDENT",
    "GOVERNOR AND LIEUTENANT GOVERNOR", "UNITED STATES SENATOR",
    "ATTORNEY GENERAL", "SECRETARY OF STATE", "COMPTROLLER", "TREASURER",
)


def _form_tokens(html):
    out = {}
    for name in ("__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION"):
        m = re.search(r'id="%s"[^>]*value="([^"]*)"' % name, html)
        if m:
            out[name] = m.group(1)
    return out


def csv_links(election_id):
    """[(office, url)] for one election, by replaying the page's own postback.

    The page shows only the election it is CURRENTLY displaying, which defaults
    to the newest — so a comparison against any past election has to select it
    first. The election dropdown carries an ASP.NET AutoPostBack, so selecting
    the option IS the submit; this replays that with the form's own three
    tokens rather than guessing a filename, because the office code and the
    election's tag ("2024GE") are not derivable from the election id.
    """
    html = _get(TOTALS, timeout=60).decode("utf-8", "replace")
    data = _form_tokens(html)
    if not data:
        fail("no ASP.NET form tokens on %s — the page's structure changed" % TOTALS)
    data.update({
        "__EVENTTARGET": "ctl00$ContentPlaceHolder1$ddlElections",
        "__EVENTARGUMENT": "",
        "ctl00$ContentPlaceHolder1$ddlElections": str(election_id),
    })
    headers = dict(UA_HINTS_CHROME_126)
    headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(TOTALS, data=urllib.parse.urlencode(data).encode(),
                                 headers=headers)
    with urllib.request.urlopen(req, timeout=120) as resp:
        page = resp.read().decode("utf-8", "replace")
    out = []
    for href in re.findall(r'href="([^"]*ByOffice[^"]*\.csv)"', page, re.I):
        path = href.replace("\\", "/")
        if "/%s/" % election_id not in path:
            continue
        office = os.path.basename(path).rsplit("-", 1)[0].split("-", 2)[-1]
        out.append((office.upper(), BASE + urllib.parse.quote(path)))
    return out


def csv_url_for(election_id):
    """The statewide results CSV for one election, or the widest available."""
    links = csv_links(election_id)
    if not links:
        fail("election %s links no results CSV — try --list for the ids that exist"
             % election_id)
    for want in STATEWIDE_OFFICES:
        for office, url in links:
            if office == want:
                return url, office
    # No statewide office on this ballot (a consolidated election has none).
    # Take the first and let the caller report how many authorities it covered.
    return links[0][1], links[0][0]


def precincts_for(election_id):
    """({AUTHORITY: {precinct name}}, office) for one election."""
    url, office = csv_url_for(election_id)
    rows = csv.DictReader(io.StringIO(_get(url).decode("utf-8-sig", "replace")))
    out = collections.defaultdict(set)
    for row in rows:
        name = (row.get("PrecinctName") or "").strip()
        if not name or is_ballot_class(name):
            continue
        out[(row.get("JurisName") or "").strip().upper()].add(
            precinct_key(name.upper()))
    if not out:
        fail("election %s's CSV parsed to zero precincts — the columns changed "
             "(expected JurisName + PrecinctName)" % election_id)
    return out, office


# A change that survives the id strip can still be COSMETIC — the county
# restyling its labels rather than moving a line. Measured on the 2024-to-2026
# pair, all four remaining shipped-county findings are exactly this: Hancock and
# Jefferson gained a full stop (ST ALBANS -> ST. ALBANS, MT VERNON -> MT. VERNON),
# Menard put spaces around a hyphen (NORTH ATHENS-CITY -> NORTH ATHENS - CITY),
# and Warren collapsed a double space (MONMOUTH  1 -> MONMOUTH 1).
#
# These are NOT filtered out, because a renamed precinct is a real event for this
# repo: several builders join a county's precincts to census geography BY NAME
# (the Jasper test), and every one of those joins breaks on a full stop. They are
# LABELLED instead, so a reader can tell in one line whether to rebuild geometry
# or to fix an alias.
def _loose(name):
    return re.sub(r"[^A-Z0-9]", "", name.upper())


def classify(gone, added):
    """'cosmetic' when the two sides differ only in punctuation or spacing."""
    return ("cosmetic" if {_loose(x) for x in gone} == {_loose(x) for x in added}
            else "fabric")


def compare(older, newer, only=None):
    a, office_a = precincts_for(older)
    b, office_b = precincts_for(newer)
    print("  read %s via %s (%d authorities) and %s via %s (%d authorities)"
          % (older, office_a, len(a), newer, office_b, len(b)), file=sys.stderr)
    shared = sorted(set(a) & set(b))
    if only:
        shared = [j for j in shared if only.upper() in j]
    moved = []
    for juris in shared:
        gone, added = sorted(a[juris] - b[juris]), sorted(b[juris] - a[juris])
        if gone or added:
            moved.append((juris, len(a[juris]), len(b[juris]), gone, added,
                          classify(gone, added)))
    return moved, shared, sorted(set(a) ^ set(b))


# ---------------------------------------------------------------------------
# THE JASPER TEST, run against the CENSUS rather than against another election.
#
# The comparison above is election-to-election, which is the right shape for a
# tripwire on a SHIPPED layer. The research question that comes first is a
# different one: is a county's fabric still the Census 2020 fabric at all, so
# that a dissolve of census geometry can answer for it? That is the Jasper test,
# and the guidebook MEASURED its error rate on 2026-08-20 across all 33 frontier
# counties: a naive name comparison matched 9 of 32, and normalising four
# mechanical causes took it to 19 of 32. TEN COUNTIES — 31% — were rejected for
# reasons that are not a moved fabric, and "a builder following the recipe as
# written would have recorded each of them as re-precincted and stopped."
#
# That measurement then sat in the guidebook and nowhere else, which is this
# repo's own named failure mode. This is it made re-runnable.
#
# EACH CAUSE IS SAFE BY CONSTRUCTION, not by judgement, and each is REPORTED:
# the rule is that a name mismatch is a HYPOTHESIS, never a verdict, and the
# reader is owed which cause was ruled out. Nothing here decides a county is
# buildable; it decides which differences are still worth reading.
#
#   1. Census truncates BASENAME at 17 characters. COMPROMISE GIFFOR is the
#      county's COMPROMISE GIFFORD. Applied only when the census name is
#      EXACTLY 17 characters, prefixes the county name, and exactly one
#      unmatched county name qualifies — so it can never merge two precincts.
#   2. Zero-padding. CUNNINGHAM 01 against CUNNINGHAM 1, throughout Champaign.
#      Applied only when depadding produces a name the county actually has.
#   3. A vestigial trailing 1 or I on single-precinct townships. The census
#      writes CAVE 1, UNION 1, LARKINSBURG I where the county writes CAVE,
#      UNION, LARKINSBURG. Applied ONLY when no `2`/`II` sibling exists on
#      EITHER side — the condition that makes it safe rather than plausible.
#   4. ISBE reporting-unit suffixes, already stripped by precinct_key above.
#      Reported here rather than re-applied, because it CUTS BOTH WAYS: it is
#      also the tell that a county subdivides precincts for reporting, which is
#      what a county does when district lines cut through them.
#
# RUNNING IT CORRECTED THE RECORD IN TWO WAYS, 2026-09-04.
#
#   * THE CAUSES ARE NOT ONE-DIRECTIONAL. The guidebook describes each as a
#     census habit — "the census writes CAVE 1 where the county writes CAVE",
#     "CUNNINGHAM 01 vs CUNNINGHAM 1" — and both run the other way too:
#     CHAMPAIGN's county writes the padded 01 against the census's 1, and
#     WARREN's county writes BERWICK 1 against the census's BERWICK. Every
#     canonicaliser here therefore runs on BOTH sides. Tried one-way first,
#     which left Champaign and Warren unreconciled and looking re-precincted.
#
#   * THERE IS A FIFTH CAUSE: roman ordinals (see _canon_roman). Clay's census
#     reads HARTER III where the county reads HARTER 3. It was never in the
#     four, and this repo already knew about it — title_case has carried
#     _ROMAN_ORDINAL since Scott shipped.
#
#   * AND A SIXTH: a spelled-out unit word one publisher carries and the other
#     does not (see _canon_unit_word). Adams writes BEVERLY PCT 1 against the
#     census's BEVERLY. Measured as a small tail — five counties statewide —
#     and implemented anyway, because a cause left out of the tool is a cause
#     the next pass re-derives, which is this file's whole reason for existing.
#
#   And one guard is STRICTER than the guidebook's: it says strip a vestigial 1
#   when the stem has "no 2 sibling", and CLAY's HARTER runs 1, 3, 4, 5, 6, 7
#   with no 2 at all — so the test reads ANY other ordinal on the stem.
#
# EVERY CANONICALISER IS ALSO REFUSED IF IT WOULD COLLAPSE TWO NAMES INTO ONE.
# That guard was missing from the first draft and is not hypothetical: each rule
# maps two spellings onto one, so a county holding WARD 01 beside WARD 1 would
# have lost a real precinct — and the loss would have made the counts agree,
# which is precisely the evidence this tool reports as "the fabric did not move".
#
# MEASURED over all 100 counties that reported in the 2026 General Primary:
# naive 29, reconciled 42, 14 more differing only on a SPELLING (which is what
# apply_aliases is for) and 44 on the COUNT, which is a fabric that really moved.
#
# THE VALIDATION THAT MATTERS is the 33 counties whose precinct layers this app
# already ships from census geometry, whose fabric is therefore independently
# known current: 22 reconcile, and every one of the other 11 is accounted for —
# Calhoun is the COMPOSED shape (5 precincts over 7 voting districts, which
# check_fabric_composed exists for), six are aliases their builders already
# carry, and three (McDonough, Ogle, Stephenson) are real consolidations, with
# McDonough being the county CI caught drifting in August. Nothing in that set
# is unexplained, which is the evidence the five causes are neither too loose
# nor too tight.
# ---------------------------------------------------------------------------

CENSUS2020 = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
              "tigerWMS_Census2020/MapServer")
CENSUS_TRUNCATION_LEN = 17


def _norm(name):
    """Mirrors vtd_board_districts.norm DELIBERATELY rather than importing it.

    That module imports requests and build_metro_outline at module scope, and
    this script is stdlib-only on purpose — it is a research tool that should
    run anywhere. --selftest asserts the two agree, so a divergence fails
    rather than going unnoticed."""
    return re.sub(r"[^A-Z0-9]", "", (name or "").upper())


def _census_json(layer, params):
    query = dict(params)
    query.update({"f": "json", "returnGeometry": "false"})
    url = "%s/%d/query?%s" % (CENSUS2020, layer, urllib.parse.urlencode(query))
    return json.loads(_get(url).decode("utf-8", "replace"))


def census_county_fips():
    """{COUNTY NAME: fips} for all 102 Illinois counties, from TIGERweb.

    Fetched rather than tabled: a name-to-FIPS table in this file would be one
    more hand-kept claim about the world, and the same host already answers."""
    data = _census_json(82, {"where": "STATE='17'", "outFields": "BASENAME,COUNTY"})
    out = {}
    for feature in data.get("features") or []:
        attrs = feature.get("attributes") or {}
        name = " ".join(str(attrs.get("BASENAME") or "").upper().split())
        if name:
            out[name] = str(attrs.get("COUNTY"))
    if len(out) < 102:
        fail("the census county layer returned %d Illinois counties, expected 102"
             % len(out))
    return out


def census_vtd_names(fips):
    """The county's Census 2020 voting-district BASENAMEs, verbatim."""
    data = _census_json(58, {"where": "STATE='17' AND COUNTY='%s'" % fips,
                             "outFields": "BASENAME"})
    return {" ".join(str((f.get("attributes") or {}).get("BASENAME") or "")
                     .upper().split())
            for f in (data.get("features") or [])} - {""}


def _cause_truncation(a, b):
    """Cause 1 — {name in a: name in b} for 17-character census truncations.

    Pairwise by nature: a truncated name cannot be canonicalised, only paired.
    Guarded three ways so it can never merge two precincts — the short name is
    EXACTLY 17 characters, it prefixes the long one, and exactly one unmatched
    candidate qualifies."""
    a_norms, b_norms = {_norm(x) for x in a}, {_norm(x) for x in b}
    out = {}
    for x in sorted(a):
        if len(x) != CENSUS_TRUNCATION_LEN or _norm(x) in b_norms:
            continue
        hits = [c for c in sorted(b)
                if _norm(c).startswith(_norm(x)) and _norm(c) not in a_norms]
        if len(hits) == 1:
            out[x] = hits[0]
    return out


# The same alphabet and length limit vtd_board_districts._ROMAN_ORDINAL uses,
# and for the same measured reason: widening it mangles real place names, since
# DIX is a village in Jefferson County and a valid 509, and MI is a valid 1001.
_ROMAN_ORDINAL = re.compile(r"^(X{0,3})(IX|IV|V?I{0,3})$")
_ROMAN_VALUE = {"I": 1, "V": 5, "X": 10}


def _roman_to_int(token):
    """The token's value, or None if it is not a plausible precinct ordinal."""
    token = token.upper()
    if not token or len(token) > 4 or not _ROMAN_ORDINAL.match(token):
        return None
    total = prev = 0
    for ch in reversed(token):
        value = _ROMAN_VALUE[ch]
        total += -value if value < prev else value
        prev = max(prev, value)
    return total or None


def _canon_roman(name):
    """Cause 5 — a trailing roman ordinal written as arabic.

    NOT IN THE GUIDEBOOK'S FOUR, and measured into existence on 2026-09-04:
    Clay's census reads HARTER III where the county reads HARTER 3, and
    Hancock's CARTHAGE II against CARTHAGE 2. The conversion is one this repo
    already knew about — title_case has carried _ROMAN_ORDINAL since Scott
    shipped — it had simply never been part of the fabric comparison."""
    parts = name.split()
    if len(parts) < 2:
        return name
    value = _roman_to_int(parts[-1])
    return " ".join(parts[:-1] + [str(value)]) if value else name


_PADDED = re.compile(r"\b0+(\d)")


def _canon_padding(name):
    """Cause 2 — zero-padding. CUNNINGHAM 01 and CUNNINGHAM 1 are one precinct.

    Applied to BOTH sides, which is the correction of 2026-09-04: the guidebook
    records this as a census habit, and Champaign runs it the other way — the
    COUNTY writes 01 and the census writes 1. A cause that is only ever tried
    in one direction misses half of its own instances."""
    return _PADDED.sub(r"\1", name)


_TRAILING_ONE = re.compile(r"\s+(?:1|I)$")
_ORDINAL_TAIL = re.compile(r"\s+([0-9]{1,3}|[IVX]{1,4})$")


def _stems_with_other_ordinals(names):
    """Stems that carry an ordinal OTHER than 1 — the condition that makes
    dropping a vestigial 1 safe.

    STRICTER THAN THE GUIDEBOOK'S "no 2 sibling", and Clay is why: its HARTER
    runs 1, 3, 4, 5, 6, 7 with no 2 at all, so a no-2 test would have stripped
    a genuinely numbered precinct's ordinal. Any other ordinal on the stem
    means the 1 is doing work."""
    out = set()
    for name in names:
        match = _ORDINAL_TAIL.search(name)
        if not match:
            continue
        tail = match.group(1)
        value = int(tail) if tail.isdigit() else _roman_to_int(tail)
        if value and value != 1:
            out.add(_norm(_ORDINAL_TAIL.sub("", name)))
    return out


def _canon_vestigial_one(name, protected):
    """Cause 3 — a vestigial trailing 1 or I on a single-precinct township.

    The census writes CAVE 1, UNION 1, LARKINSBURG I where Franklin and Union
    write CAVE, UNION, LARKINSBURG — and Warren runs it the OTHER WAY, its
    county writing BERWICK 1 against the census's BERWICK, which is the second
    half of the same 2026-09-04 direction correction."""
    if not _TRAILING_ONE.search(name):
        return name
    stem = _TRAILING_ONE.sub("", name)
    return name if _norm(stem) in protected else stem


# Canonicalisers run on BOTH name sets; truncation is pairwise and runs last,
# once the cheap normalisations have removed the noise it would otherwise have
# to pair through.
_UNIT_WORD = re.compile(r"\s+(?:PCT|PRECINCT|TWP|TOWNSHIP)\b", re.I)


def _canon_unit_word(name):
    """Cause 6 — a spelled-out unit word one publisher includes and the other
    does not: Adams writes BEVERLY PCT 1 against the census's BEVERLY, and
    CAMP POINT PCT 1 against CAMP POINT 1; McDonough's MACOMB TOWNSHIP is the
    census's MACOMB TWP.

    MEASURED 2026-09-04 rather than assumed, and it is a SMALL tail: five
    counties statewide (Adams and Will on PCT, Brown and McDonough on
    TOWNSHIP, Fulton and McDonough on TWP, Monroe on PRECINCT). Recorded and
    implemented anyway, because a cause left out of the tool is a cause the
    next pass re-derives — which is the whole reason this file exists. Dropping
    the token is safe on its face (no Illinois precinct is NAMED Pct or Twp),
    and the collapse guard above catches the case where it would not be."""
    return _UNIT_WORD.sub("", name).strip()


JASPER_CANONICAL = (
    ("roman ordinal -> arabic", _canon_roman),
    ("zero-padding", _canon_padding),
    ("unit word (PCT/TWP/TOWNSHIP)", _canon_unit_word),
)


def jasper(county_names, census_names):
    """(matched, applied, county_only, census_only) for one county.

    Every cause is applied to BOTH sides and kept only if it STRICTLY reduces
    the disagreement, so a rule that fires without helping is discarded rather
    than recorded as a reconciliation that did nothing."""
    county, census = set(county_names), set(census_names)
    applied = []

    def diff(x, y):
        return len({_norm(n) for n in x} ^ {_norm(n) for n in y})

    def keep(trial_a, trial_b):
        """A canonicaliser may only be adopted if it HELPS and LOSES NOTHING.

        The second half was missing until 2026-09-04 and is not hypothetical:
        every rule here maps two spellings onto one, so a county holding both
        forms — WARD 01 beside WARD 1, HARTER I beside HARTER 1, CAVE 1 beside
        CAVE — would have had two real precincts silently collapsed into one,
        and the collapse would have made the counts agree, which is exactly the
        evidence this tool reports as "the fabric did not move"."""
        return (diff(trial_a, trial_b) < diff(county, census)
                and len(trial_a) == len(county) and len(trial_b) == len(census))

    for label, canon in JASPER_CANONICAL:
        trial_a = {canon(n) for n in county}
        trial_b = {canon(n) for n in census}
        if keep(trial_a, trial_b):
            county, census = trial_a, trial_b
            applied.append((label, None))

    protected = _stems_with_other_ordinals(county | census)
    trial_a = {_canon_vestigial_one(n, protected) for n in county}
    trial_b = {_canon_vestigial_one(n, protected) for n in census}
    if keep(trial_a, trial_b):
        county, census = trial_a, trial_b
        applied.append(("vestigial trailing 1/I", None))

    pairs = _cause_truncation(census, county) or _cause_truncation(county, census)
    if pairs:
        for side in (census, county):
            hit = set(pairs) & side
            if hit:
                side -= hit
                side |= {pairs[h] for h in hit}
        applied.append(("census 17-char truncation", pairs))

    cn = {_norm(c): c for c in county}
    xn = {_norm(c): c for c in census}
    county_only = sorted(cn[k] for k in set(cn) - set(xn))
    census_only = sorted(xn[k] for k in set(xn) - set(cn))
    return (not county_only and not census_only), applied, county_only, census_only


def shipped_counties():
    """{NORMALISEDNAME: path} for every county whose precincts this app ships."""
    out = {}
    for path in sorted(glob.glob(os.path.join(REPO_ROOT, "il", "data", "app",
                                              "*-precincts.json"))):
        slug = os.path.basename(path).replace("-precincts.json", "")
        out[re.sub(r"[^A-Z]", "", slug.upper())] = path
    return out


def run_jasper(election_id, only=None):
    """Per county: is its CURRENT precinct fabric still the Census 2020 fabric?"""
    by_authority, office = precincts_for(election_id)
    fips = census_county_fips()
    print("  read election %s via %s (%d authorities); census county layer "
          "answered for %d counties" % (election_id, office, len(by_authority),
                                        len(fips)), file=sys.stderr)
    names = sorted(n for n in fips if not only or only.upper() in n)
    naive_ok = reconciled_ok = looked = 0
    rows = []
    for name in names:
        county = by_authority.get(name)
        if not county:
            continue          # a county whose ballot this election did not carry,
            # or one whose returns are filed by a city election commission under
            # its own JurisName — either way there is nothing to compare here.
        census = census_vtd_names(fips[name])
        if not census:
            continue
        looked += 1
        naive = {_norm(c) for c in county} == {_norm(c) for c in census}
        ok, applied, county_only, census_only = jasper(county, census)
        naive_ok += bool(naive)
        reconciled_ok += bool(ok)
        rows.append((name, len(county), len(census), naive, ok, applied,
                     county_only, census_only))
    alias_only = sum(1 for r in rows if not r[4] and r[1] == r[2])
    fabric = sum(1 for r in rows if not r[4] and r[1] != r[2])
    print("\nisbe-precinct-fabric --jasper: %d county(ies) compared\n"
          "  naive name comparison        %d match\n"
          "  after the six causes         %d match\n"
          "  still differing              %d on a SPELLING (an alias closes it)\n"
          "                               %d on the COUNT (the fabric moved)"
          % (looked, naive_ok, reconciled_ok, alias_only, fabric))
    for name, nc, nx, naive, ok, applied, county_only, census_only in rows:
        if naive:
            continue          # matched before any rule ran; nothing to report
        # THE SPLIT A READER ACTUALLY NEEDS, and it is derivable rather than
        # judged: when the two sides still differ but COUNT THE SAME, the fabric
        # did not move and what is left is a spelling — the case apply_aliases
        # exists for. When the count itself moved, precincts were consolidated
        # or split and no alias can fix it. Measured across the 33 counties
        # whose precincts this app ships, every same-count residual is an alias
        # its builder already carries (Hancock's MONTIBELLO, White's GREY,
        # Schuyler's FREDRICK, Jefferson's MOUNT vs MT.), and every
        # count-moved one is a real consolidation — McDonough, Ogle and
        # Stephenson, McDonough being the county CI caught drifting in August.
        if ok:
            verdict = "RECONCILED"
        elif nc == nx:
            verdict = "DIFFERS: same count — a spelling, so an ALIAS"
        else:
            verdict = "DIFFERS: count moved %d -> %d — a FABRIC change" % (nx, nc)
        print("\n  %s [%s] — %d county precinct(s), %d census voting district(s)"
              % (name, verdict, nc, nx))
        for label, pairs in applied:
            if pairs:                      # the pairwise cause names its pairs
                sample = ", ".join("%s -> %s" % (a, b)
                                   for a, b in sorted(pairs.items())[:3])
                print("      ruled out: %s (%d) — %s" % (label, len(pairs), sample))
            else:                          # a canonicaliser ran on both sides
                print("      ruled out: %s" % label)
        if county_only:
            print("      county-only: %s%s" % (", ".join(county_only[:8]),
                                               " …" if len(county_only) > 8 else ""))
        if census_only:
            print("      census-only: %s%s" % (", ".join(census_only[:8]),
                                               " …" if len(census_only) > 8 else ""))
    return 0


def selftest():
    """The guidebook's own worked examples, run as assertions. No network."""
    checks = []

    def ok(label, got, want):
        checks.append((label, got == want, got, want))

    # norm must not drift from the module that owns the real one.
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from vtd_board_districts import norm as shared_norm  # noqa: PLC0415
        ok("norm matches vtd_board_districts.norm",
           [_norm(s) for s in ("Clay City I", "ROBINSON  1", "St. Albans")],
           [shared_norm(s) for s in ("Clay City I", "ROBINSON  1", "St. Albans")])
    except Exception as exc:  # noqa: BLE001 - the tool must run stdlib-only
        checks.append(("norm cross-check skipped (%s)" % type(exc).__name__,
                       True, None, None))

    # 1. Champaign's truncations, and names that must NOT be touched.
    ok("truncation: COMPROMISE GIFFOR -> COMPROMISE GIFFORD",
       _cause_truncation({"COMPROMISE GIFFOR", "COMPROMISE PENFIE"},
                         {"COMPROMISE GIFFORD", "COMPROMISE PENFIELD"}),
       {"COMPROMISE GIFFOR": "COMPROMISE GIFFORD",
        "COMPROMISE PENFIE": "COMPROMISE PENFIELD"})
    ok("truncation: refuses when two candidates share the prefix",
       _cause_truncation({"COMPROMISE GIFFOR"},
                         {"COMPROMISE GIFFORD", "COMPROMISE GIFFORDX"}), {})
    ok("truncation: refuses a name that is not exactly 17 characters",
       _cause_truncation({"CAVE"}, {"CAVE TOWNSHIP"}), {})

    # 2. Zero-padding, canonical on both sides.
    ok("zero-padding: CUNNINGHAM 01 -> CUNNINGHAM 1",
       _canon_padding("CUNNINGHAM 01"), "CUNNINGHAM 1")
    ok("zero-padding: leaves a real 10 alone", _canon_padding("WARD 10"), "WARD 10")

    # 5. Roman ordinals — the cause the guidebook's four never named.
    ok("roman: HARTER III -> HARTER 3", _canon_roman("HARTER III"), "HARTER 3")
    ok("roman: CARTHAGE II -> CARTHAGE 2", _canon_roman("CARTHAGE II"), "CARTHAGE 2")
    # These two exercise the ALPHABET, which is the guard that matters. An
    # earlier version asserted _canon_roman("DIX") == "DIX" and passed with the
    # alphabet widened to LCDM — because a one-token name returns early and the
    # alphabet was never consulted. Green for the wrong reason; the names below
    # carry a second token so the tail really is tested.
    ok("roman: leaves a DIX tail alone (a village, and a valid 509)",
       _canon_roman("SOUTH DIX"), "SOUTH DIX")
    ok("roman: leaves an MI tail alone (a valid 1001)",
       _canon_roman("WARD MI"), "WARD MI")
    ok("roman: leaves DIX alone as a whole name too",
       _canon_roman("DIX"), "DIX")
    ok("roman: leaves a name whose tail is not an ordinal alone",
       _canon_roman("SPRING POINT"), "SPRING POINT")

    # 3. The vestigial 1/I, and the sibling condition that makes it safe.
    free = _stems_with_other_ordinals({"CAVE 1", "AVENA 1", "LARKINSBURG I"})
    ok("vestigial 1: CAVE 1 -> CAVE when the stem has no other ordinal",
       [_canon_vestigial_one(n, free)
        for n in ("CAVE 1", "AVENA 1", "LARKINSBURG I")],
       ["CAVE", "AVENA", "LARKINSBURG"])
    held = _stems_with_other_ordinals({"CAVE 1", "CAVE 2"})
    ok("vestigial 1: refuses when a 2 sibling exists (real numbering)",
       _canon_vestigial_one("CAVE 1", held), "CAVE 1")
    # Clay's HARTER runs 1, 3, 4, 5, 6, 7 with NO 2 — the case a "no 2 sibling"
    # rule would have got wrong, which is why the guard reads any other ordinal.
    clay = _stems_with_other_ordinals({"HARTER 1", "HARTER 3", "HARTER 7"})
    ok("vestigial 1: refuses HARTER 1 on a stem numbered 3..7 with no 2",
       _canon_vestigial_one("HARTER 1", clay), "HARTER 1")
    ok("vestigial 1: the guard sees ROMAN siblings too",
       _canon_vestigial_one("HARTER I", _stems_with_other_ordinals(
           {"HARTER I", "HARTER III"})), "HARTER I")

    # 6. The unit word, and the guard that keeps it from eating a real name.
    ok("unit word: BEVERLY PCT 1 -> BEVERLY 1",
       _canon_unit_word("BEVERLY PCT 1"), "BEVERLY 1")
    ok("unit word: MACOMB TOWNSHIP -> MACOMB", _canon_unit_word("MACOMB TOWNSHIP"),
       "MACOMB")
    ok("unit word: leaves a name with no unit token alone",
       _canon_unit_word("SPRING POINT"), "SPRING POINT")

    # THE COLLAPSE GUARD. Every canonicaliser maps two spellings onto one, so a
    # county holding BOTH forms would lose a real precinct — and the loss would
    # make the counts agree, which is the very evidence this tool reports as
    # "the fabric did not move". A rule that would collapse is refused.
    matched, applied, county_only, census_only = jasper(
        {"WARD 1", "WARD 01"}, {"WARD 1", "WARD 2"})
    ok("collapse guard: refuses zero-padding that would merge WARD 01 into WARD 1",
       (matched, len(applied), county_only, census_only),
       (False, 0, ["WARD 01"], ["WARD 2"]))
    matched, _, _, _ = jasper({"CAVE", "CAVE 1"}, {"CAVE", "CAVE 1"})
    ok("collapse guard: an already-matching pair is left exactly alone",
       matched, True)

    # 4. Already applied upstream by precinct_key; asserted here so all six
    #    causes are testable in one place.
    ok("reporting id: SPRING POINT-7 -> SPRING POINT",
       precinct_key("SPRING POINT-7"), "SPRING POINT")
    ok("reporting id: leaves Calhoun's merged names alone",
       [precinct_key(n) for n in ("HARDIN-GILEAD", "BELLEVIEW-HAMBURG")],
       ["HARDIN-GILEAD", "BELLEVIEW-HAMBURG"])

    # The whole reconciliation, end to end, in BOTH directions.
    matched, applied, county_only, census_only = jasper(
        {"CAVE", "CUNNINGHAM 1", "COMPROMISE GIFFORD"},
        {"CAVE 1", "CUNNINGHAM 01", "COMPROMISE GIFFOR"})
    ok("end to end: census-side causes reconcile a county exactly",
       (matched, county_only, census_only), (True, [], []))
    matched, _, county_only, census_only = jasper(
        {"BERWICK 1", "CUNNINGHAM 01"}, {"BERWICK", "CUNNINGHAM 1"})
    ok("end to end: the SAME causes running county-side (Warren, Champaign)",
       (matched, county_only, census_only), (True, [], []))
    matched, _, county_only, _ = jasper({"HURRICANE"},
                                        {"NORTH HURRICANE", "SOUTH HURRICANE"})
    ok("end to end: a REAL split still differs (Fayette's HURRICANE)",
       (matched, county_only), (False, ["HURRICANE"]))

    bad = [c for c in checks if not c[1]]
    for label, good, got, want in checks:
        print("  %s %s" % ("ok " if good else "FAIL", label))
        if not good:
            print("       got  %r\n       want %r" % (got, want))
    if bad:
        print("isbe-precinct-fabric --selftest: FAIL — %d of %d check(s)"
              % (len(bad), len(checks)), file=sys.stderr)
        return 1
    print("isbe-precinct-fabric --selftest: OK — %d check(s)" % len(checks))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--list", action="store_true", help="list election ids")
    ap.add_argument("--compare", nargs=2, metavar=("OLDER", "NEWER"),
                    help="two election ids, oldest first")
    ap.add_argument("--county", help="limit the comparison to one authority")
    ap.add_argument("--shipped", action="store_true",
                    help="report only counties whose precincts this app ships")
    ap.add_argument("--jasper", metavar="ELECTION",
                    help="run THE JASPER TEST for every county: this election's "
                         "ISBE precinct names against Census 2020 voting districts")
    ap.add_argument("--selftest", action="store_true",
                    help="check the four reconciliation causes on the guidebook's "
                         "own worked examples (no network)")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    # ISBE refuses this project: www.elections.il.gov/robots.txt is a
    # BOM'd `User-agent: * / Disallow: /`, Last-Modified 2025-06-12, measured
    # 2026-09-25. The full record is in scripts/il_county_clerk_scraper.py's
    # main() and in scripts/robots_policy.py's `_parse`, whose BOM defect is why
    # a year-old refusal read as a permission. Nothing is fetched from this host;
    # files already built from it keep their records (CLAUDE.md, Adam 2026-09-19).
    #
    # THIS CLOSES THE RE-PRECINCTING TRIPWIRE THIS MODULE IS. Its docstring
    # explains that most Illinois precinct layers are a Census 2020 snapshot and
    # that ISBE was the only source carrying all 102 authorities, so nothing else
    # can run the comparison today. The gate sits AFTER --selftest deliberately:
    # that path is offline, runs in CI, and proves the parser for the day a route
    # reopens. Every other flag fetches, so every other flag stops here.
    require_robots_allowed(TOTALS, UA_HINTS_CHROME_126["User-Agent"],
                           headers=UA_HINTS_CHROME_126,
                           label="isbe-precinct-fabric")

    if args.jasper:
        return run_jasper(args.jasper, args.county)

    if args.list:
        print("  id   election                       results CSVs")
        for eid, label in elections():
            try:
                links = csv_links(eid)
            except Exception:  # noqa: BLE001 - a listing must not die on one row
                links = []
            offices = {o for o, _ in links}
            wide = next((o for o in STATEWIDE_OFFICES if o in offices), None)
            note = ("%2d  (statewide: %s)" % (len(links), wide) if wide
                    else "%2d  %s" % (len(links),
                                      "(none — consolidated elections carry no CSVs)"
                                      if not links else "(no statewide office; a subset)"))
            print("  %-4s %-30s %s" % (eid, " ".join(label.split()), note))
        return
    if not args.compare:
        ap.print_help()
        return

    older, newer = args.compare
    moved, shared, only_one = compare(older, newer, args.county)
    total_moved = len(moved)
    if args.shipped:
        ships = shipped_counties()
        moved = [m for m in moved if re.sub(r"[^A-Z]", "", m[0].upper()) in ships]
    print("isbe-precinct-fabric: %d authority(ies) reported in both elections; "
          "%d changed their precinct names%s"
          % (len(shared), total_moved,
             "; %d of them are counties whose precincts this app ships" % len(moved)
             if args.shipped else ""))
    if only_one:
        print("  (in one election only, not compared: %s)" % ", ".join(only_one[:6]))
    kinds = collections.Counter(m[5] for m in moved)
    if moved:
        print("  %d fabric change(s), %d cosmetic (punctuation or spacing only — "
              "no line moved, but a name join breaks on one)"
              % (kinds.get("fabric", 0), kinds.get("cosmetic", 0)))
    for juris, na, nb, gone, added, kind in moved:
        print("\n  %s [%s] — %d -> %d precinct(s)" % (juris, kind.upper(), na, nb))
        if gone:
            print("      gone : %s%s" % (", ".join(gone[:8]), " …" if len(gone) > 8 else ""))
        if added:
            print("      added: %s%s" % (", ".join(added[:8]), " …" if len(added) > 8 else ""))
    if not moved:
        print("  No authority changed a precinct name between these elections.")


if __name__ == "__main__":
    main()
