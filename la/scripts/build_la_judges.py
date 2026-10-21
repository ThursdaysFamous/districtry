#!/usr/bin/env python3
"""Build la/data/app/la-judges.json: every justice of the Louisiana Supreme
Court, every judge of the five courts of appeal and every judge of the
district courts, by the district each is elected from, from the Secretary of
State's list of elected officials.

WHO IS ELECTED FROM WHERE. The Supreme Court has seven justices, one elected
from each of its seven districts (La. R.S. 13:101.2). Each court of appeal
circuit is divided into three districts (La. R.S. 13:312), each electing one
or more judges, and two of the Fourth Circuit's judges are elected from the
whole circuit. Each of the 41 judicial districts (La. R.S. 13:477) elects one
or more district judges, and Orleans Parish elects the judges of its own civil
and criminal district courts. Several districts elect some of their judges
from election sections or subdistricts, which the laws and other statutes set
by voting precinct. la/scripts/build_la_court_districts.py draws the districts;
this file names who holds each seat and holds its parish lists to those maps.

THE SOURCE is the one build_la_parish_officials.py reads: the voter portal's
list of offices (https://voterportal.sos.la.gov/ElectedOfficials/Office/Index)
and its CSV export of each. Three are read here, by the index's own names:
  150_1 "Justice of the Supreme Court";
  155_1 "Judge of a Court of Appeal";
  210_1 "District Judge", which also lists Orleans Parish's civil and criminal
        district court judges, its criminal court's magistrate and the 14th
        Judicial District Court's magistrate judge.
Measured 2026-10-21: 7, 53 and 212 rows. The index's other judicial offices
(city and parish courts, juvenile and family courts, justices of the peace)
are not read: their courts are not drawn. The parish builder's --save keeps
all of the list's exports this file and build_la_local_officials.py read, so a
weekly run reads them once (--exports).

WHAT IS READ, AND WHAT IS NEVER READ, follows the parish builder, through its
own functions (person_record, office_contacts, contact_book): from each row
the title, the seat, the name, the party, the telephone, the date the term
ends and the parishes it prints, and never the race or gender the rows also
print. A telephone printed for one official alone ships on that official's
row; one printed for two or more officials is not that official's (measured
2026-10-21: a Court of Appeal judge and a St. Bernard school board member
print the same number, so it ships on neither row). An address ships only as
a court's office, where at least three of the court's judges print the same
one and no official outside the court does.

THE SEAT is the row's description with its abbreviations written out ("1st
Cir., 2nd Dist., Subdist. 1, Div. A" is the First Circuit's Second District,
"Subdistrict 1, Division A"; "Elec. Sect. 1C" and "ES 1" are "Election
Section 1", and the letter after a section's number is its division). A seat
elected from part of its district carries that part as its `section`
("Election Section 1", "Subdistrict 2"). In Orleans Parish a court's
"Division A" or "Section A" is a judgeship, not part of the parish: every
Orleans judge is elected parish-wide. A description this file does not know
stops the build, so a new form is read by a person before it ships.

THE PARISHES each row prints are the parishes its voters live in, and they
are held to the maps: a justice's to the parishes the Supreme Court map puts
in that district, in whole or in part; a judge elected from a whole district
to that district's parishes; and a judge elected from a section to a set
inside them. The two at-large Fourth Circuit judges' are the circuit's.

WHICH SECTION A PARISH IS IN. The law that divides a court of appeal district
into election sections names each section's parishes, whole or by precinct
(La. R.S. 13:312, kept in la/data/source/courts/). Where the list names a
judge for every one of a district's sections, and the parishes each section's
judges print are exactly the parishes the law names for that section, this
file records which of the district's parishes lie wholly in each section, so
the card can tell a reader in one of those parishes which judges their votes
elect. A parish the law divides between sections is recorded as divided, and
the card says it cannot tell which side of the line a point is on. The
district courts' sections are set by statutes this file does not read (13:477
names only some of them, and the list's sections differ from it in the 19th
Judicial District), so no district court card says which section a point is
in; each judge's seat names the section.

THE LIST NAMES WHOM IT NAMES. Nothing here reads how many seats a court has,
and the list can leave one out without saying so: on 2026-10-21 it named one
judge for the 7th Judicial District, in Division B, and three for the 18th,
from Election Sections 2, 3 and 4, and no court's own list of its judges was
read to say whether either court has another seat. So every card says how many
judges the list names rather than how many the court has. Division letters are
not consecutive in every court (the 29th Judicial District's are C, D and E),
so no card names a missing letter as a missing seat.

THE PARTY, THE TERM AND THE DATE follow the parish builder: the party as a
word; the date each term ends; and the day the list was read, kept while the
file's records are unchanged. Every district judge's term the list gave on
2026-10-21 ends on December 31, 2026, and la/WATCH.md says when to read the
list again.

Usage:
    python3 la/scripts/build_la_judges.py                # fetch the list and write
    python3 la/scripts/build_la_judges.py --exports DIR  # the list's exports from DIR
    python3 la/scripts/build_la_judges.py --save DIR     # also keep what was fetched
    python3 la/scripts/build_la_judges.py --offline DIR  # rebuild from DIR alone
    python3 la/scripts/build_la_judges.py --check        # offline: the shipped file
"""

import datetime
import json
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
REPO = os.path.dirname(INSTANCE)
sys.path.insert(0, HERE)
import build_la_parish_officials as parish  # noqa: E402  (same instance tree)
assert os.path.dirname(os.path.abspath(parish.__file__)) == HERE, parish.__file__
import build_la_court_districts as courts  # noqa: E402  (same instance tree)
assert os.path.dirname(os.path.abspath(courts.__file__)) == HERE, courts.__file__

SOURCE = parish.SOURCE
INDEX_URL = parish.INDEX_URL
APP = os.path.join(INSTANCE, "data", "app")
OUT = os.path.join(APP, "la-judges.json")
MAPS = {
    "supreme": os.path.join(APP, "la-supreme-court-districts.json"),
    "appeal": os.path.join(APP, "la-court-of-appeal-districts.json"),
    "district": os.path.join(APP, "la-district-court-districts.json"),
}
SUPREME, APPEAL, DISTRICT = parish.JUDGE_OFFICES
ORLEANS = courts.ORLEANS
CIVIL, CRIMINAL = "Civil District Court", "Criminal District Court"

# Floors catch a truncated export while tolerating a vacancy or two. On
# 2026-10-21: 7 justices, 53 court of appeal judges (two of them elected from
# the whole Fourth Circuit), and 212 district court judges and magistrates.
MIN_JUSTICES = 6
MIN_APPEAL = 48
MIN_DISTRICT = 195
# Shares of the judges named carrying a party, and their own telephone, set
# below the day's measurement so a column going missing fails. On 2026-10-21
# all 272 judges the list named printed a party, and 251 a telephone of their
# own (92%).
MIN_PARTY_SHARE = 0.9
MIN_PHONE_SHARE = 0.8

ORDINAL_RE = r"(?P<{0}>\d+)(?P<{0}_sfx>st|nd|rd|th)"
SUPREME_RE = re.compile(r"^" + ORDINAL_RE.format("n") + r" Supreme Court District of Louisiana$")
SUPREME_TITLES = {"Associate Justice", "Chief Justice"}
APPEAL_TITLE = "Judge, Court of Appeal"
AT_LARGE_RE = re.compile(r"^" + ORDINAL_RE.format("c") + r" Circuit at Large$")
APPEAL_RE = re.compile(r"^" + ORDINAL_RE.format("c") + r" Circuit, " + ORDINAL_RE.format("d") +
                       r" District(?:, Subdistrict (?P<sub>\d+))?"
                       r"(?:, Election Section (?P<es>\d+))?(?:, Division (?P<div>[A-Z]))?$")
DISTRICT_RE = re.compile(r"^" + ORDINAL_RE.format("n") + r" Judicial District(?: Court)?"
                         r"(?:, (?:(?:Election Section (?P<es>\d+)|Subdistrict (?P<sub>\d+)), )?"
                         r"Division (?P<div>[A-Z]))?$")
DISTRICT_TITLE = "District Judge"
# The two magistrates the list prints in the District Judge office: Orleans's
# criminal court's, and the 14th Judicial District Court's magistrate judge.
MAGISTRATES = {
    ("Magistrate", "Magistrate Section, Criminal District Court"): (ORLEANS, CRIMINAL),
    ("Magistrate Judge", "14th Judicial District Court"): ("14", None),
}
ORLEANS_SEATS = {
    CIVIL: re.compile(r"^Civil District Court, (?P<seat>Division [A-Z]|Domestic Section \d)$"),
    CRIMINAL: re.compile(r"^Criminal District Court, (?P<seat>Section [A-Z])$"),
}
ORLEANS_TITLE = "Judge"
# The list's abbreviations, written out (docstring). Order matters: "Subdist."
# before "Dist.", and a section's division letter after the section.
ABBREVIATIONS = [
    (re.compile(r"\bCir\.(?=,|\s|$)"), "Circuit"),
    (re.compile(r"\bSubdist\.(?=,|\s|$)"), "Subdistrict"),
    (re.compile(r"\bDist\.?(?=,|\s|$)"), "District"),
    (re.compile(r"\bDiv\.(?=,|\s|$)"), "Division"),
    (re.compile(r"\bElec\. Sect?\.(?=\s)"), "Election Section"),
    (re.compile(r"\bES(?= \d)"), "Election Section"),
    (re.compile(r"\bJDC\b"), "Judicial District Court"),
    (re.compile(r"\bElection Section (\d+)([A-Z])\b"), r"Election Section \1, Division \2"),
]
CIRCUIT_NAMES = {1: "First", 2: "Second", 3: "Third", 4: "Fourth", 5: "Fifth"}
SECTION_COUNT_RE = re.compile(r"\bThe (?P<d>first|second|third) district shall be further "
                              r"divided into (?P<n>two|three|four|five) election sections\b")
SECTION_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
SECTION_START_RE = re.compile(r"\bElection section (?P<n>one|two|three|four|five|[1-5]) "
                              r"shall (?:be composed of|consist of)\b")
LAW_SPELLINGS = {"DeSoto": "De Soto"}


def write_out(description):
    text = parish.tidy(description)
    for pattern, repl in ABBREVIATIONS:
        text = pattern.sub(repl, text)
    return text


def ordinal_ok(m, key):
    n = int(m.group(key))
    t, u = n % 100, n % 10
    want = "th" if 11 <= t <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(u, "th")
    return m.group(key + "_sfx") == want


def unknown(office, row, why):
    raise SystemExit("FAIL: office %s carries a row titled %r described %r (%s) — %s; a new "
                     "form needs a reading here" % (office, row["OfficeTitle"],
                                                    row["OfficeTitleDescription"],
                                                    row["Parish"], why))


# ---------------------------------------------------------------- the maps

def load_maps():
    """Each court's units and their parishes, from the shipped maps: the
    Supreme Court's whole and part parishes, each court of appeal district's
    parishes (St. John the Baptist's feature counts for both of its
    districts), and each judicial district's."""
    out = {"supreme": {}, "appeal": defaultdict(set), "district": {}}
    for court, path in MAPS.items():
        with open(path) as fh:
            feats = json.load(fh)["features"]
        for f in feats:
            p = f["properties"]
            if court == "supreme":
                out[court][p["unit"]] = set(p["whole"]) | set(p["part"])
            elif court == "appeal":
                for unit in p.get("units") or [p["unit"]]:
                    out[court][unit] |= set(p["counties"])
            else:
                out[court][p["unit"]] = set(p["counties"])
    out["appeal"] = dict(out["appeal"])
    circuits = defaultdict(set)
    for unit, names in out["appeal"].items():
        circuits[unit.split("-")[0]] |= names
    out["circuits"] = dict(circuits)
    return out


def fabric_by_fold():
    with open(courts.COUNTIES) as fh:
        feats = json.load(fh)["features"]
    return {parish.fold(f["properties"]["BASENAME"]): f["properties"]["BASENAME"]
            for f in feats}


def row_parishes(row, fabric, where):
    names = [parish.tidy(x) for x in row["Parish"].split(",") if parish.tidy(x)]
    out = set()
    for name in names:
        key = parish.fold(name)
        if key not in fabric:
            raise SystemExit("FAIL: %s's row names a parish %r that matches no Census parish"
                             % (where, name))
        out.add(fabric[key])
    if not out:
        raise SystemExit("FAIL: %s's row names no parish" % where)
    return out


# ---------------------------------------------------------------- the law's sections

def law_sections(fabric):
    """For each court of appeal district La. R.S. 13:312 divides into election
    sections: {unit: {number: (whole, part)}}, the parishes the law names
    for each section, whole or by precinct. A section that names no parish
    (the Fifth Circuit's First District's second, which lists Jefferson
    Parish's precincts without naming the parish again) is recorded with
    none; it matters only where a district has more than one parish."""
    text = " ".join(courts.law_lines("rs13-312.txt"))
    names = sorted(set(fabric.values()) | set(LAW_SPELLINGS), key=len, reverse=True)
    starts = list(courts.DISTRICT_RE.finditer(text))
    out = {}
    for i, m in enumerate(starts):
        c, d = courts.CIRCUIT_WORDS[m.group("c")], courts.CIRCUIT_WORDS[m.group("d")]
        unit = "%d-%d" % (c, d)
        tail = text[m.end():starts[i + 1].start() if i + 1 < len(starts) else len(text)]
        # The next circuit's heading ends a district's text.
        cut = re.search(r"\b\d\.\(a\) ", tail)
        if cut:
            tail = tail[:cut.start()]
        count = SECTION_COUNT_RE.search(tail)
        if not count:
            continue
        if courts.CIRCUIT_WORDS[count.group("d")] != d:
            raise SystemExit("FAIL: 13:312's text after district %s divides the %s district"
                             % (unit, count.group("d")))
        want = SECTION_WORDS[count.group("n")]
        paras = list(SECTION_START_RE.finditer(tail))
        numbers = [SECTION_WORDS.get(p.group("n")) or int(p.group("n")) for p in paras]
        if numbers != list(range(1, want + 1)):
            raise SystemExit("FAIL: 13:312 divides district %s into %d election sections but "
                             "composes sections %s" % (unit, want, numbers))
        sections = {}
        for j, p in enumerate(paras):
            body = tail[p.end():paras[j + 1].start() if j + 1 < len(paras) else len(tail)]
            whole, part = set(), set()
            for name in names:
                pat = re.compile(r"\b" + re.escape(name) + r"\b")
                if not pat.search(body):
                    continue
                base = LAW_SPELLINGS.get(name, name)
                # "Precincts 1, 2 and 5A of Morehouse Parish" is part of it;
                # "Tensas Parish" or "the parishes of Bienville, ..." whole.
                if re.search(r"[Pp]recincts? [0-9A-Za-z&,\- ]*? of " + re.escape(name) +
                             r" Parish\b", body):
                    part.add(base)
                else:
                    whole.add(base)
                body = pat.sub(" ", body)
            sections[numbers[j]] = (whole, part)
        out[unit] = sections
    return out


# ---------------------------------------------------------------- reading rows

def person(row, where, book, notes, seat=None, **extra):
    rec = parish.person_record(row, seat, where, book, notes)
    for k, v in extra.items():
        if v is not None:
            rec[k] = v
    return rec


def one_per_seat(entries, where, notes):
    """(key, row) pairs with a person listed twice under one seat kept once,
    with the later term; two different people under one seat stop the
    build."""
    kept = {}
    for key, row in entries:
        if key in kept:
            other = kept[key]
            if parish.person_key(other) != parish.person_key(row):
                raise SystemExit("FAIL: the list seats two people in %s %s"
                                 % (where, " ".join(str(k) for k in key if k)))
            notes.append("%s: the list prints %s twice; one record is kept"
                         % (where, parish.person_name(row)))
            # A row with no end date sorts first, so a dated row is kept.
            if ((parish.iso_date(row["ExpDate"], where) or "") >
                    (parish.iso_date(other["ExpDate"], where) or "")):
                kept[key] = row
            continue
        kept[key] = row
    return kept


def build_supreme(texts, maps, fabric, book, notes):
    entries = []
    for row in parish.rows_of(texts[SUPREME], SUPREME):
        desc = write_out(row["OfficeTitleDescription"])
        m = SUPREME_RE.match(desc)
        if row["OfficeTitle"] not in SUPREME_TITLES or not m or not ordinal_ok(m, "n"):
            unknown(SUPREME, row, "not a Supreme Court district")
        unit = m.group("n")
        if unit not in maps["supreme"]:
            unknown(SUPREME, row, "the map has no District %s" % unit)
        got = row_parishes(row, fabric, "Supreme Court District %s" % unit)
        if got != maps["supreme"][unit]:
            raise SystemExit("FAIL: the list's justice for District %s is elected by %s, and the "
                             "map's District %s takes in %s" % (unit, sorted(got), unit,
                                                               sorted(maps["supreme"][unit])))
        entries.append(((unit,), row))
    kept = one_per_seat(entries, "Supreme Court District", notes)
    districts = {}
    for (unit,), row in sorted(kept.items(), key=lambda kv: int(kv[0][0])):
        districts[unit] = {"members": [person(row, "Supreme Court District %s" % unit, book, notes)]}
    for unit in sorted(set(maps["supreme"]) - set(districts), key=int):
        notes.append("Supreme Court District %s: the list names no justice" % unit)
    court = {"districts": districts}
    office = office_of([r for r in kept.values()], book, "the Supreme Court", notes)
    if office:
        court["office"] = office
    return court


def appeal_seat(m):
    parts = []
    if m.group("sub"):
        parts.append("Subdistrict %s" % m.group("sub"))
    if m.group("es"):
        parts.append("Election Section %s" % m.group("es"))
    section = parts[0] if parts else None
    if len(parts) > 1:
        return None, None
    if m.group("div"):
        parts.append("Division %s" % m.group("div"))
    return (", ".join(parts) or None), section


def build_appeal(texts, maps, fabric, book, law, notes):
    district_rows, at_large_rows = [], defaultdict(list)
    for row in parish.rows_of(texts[APPEAL], APPEAL):
        if row["OfficeTitle"] != APPEAL_TITLE:
            unknown(APPEAL, row, "not titled %r" % APPEAL_TITLE)
        desc = write_out(row["OfficeTitleDescription"])
        big = AT_LARGE_RE.match(desc)
        if big:
            if not ordinal_ok(big, "c") or big.group("c") not in maps["circuits"]:
                unknown(APPEAL, row, "no such circuit")
            c = big.group("c")
            got = row_parishes(row, fabric, "the %s Circuit at large" % CIRCUIT_NAMES[int(c)])
            if got != maps["circuits"][c]:
                raise SystemExit("FAIL: an at-large %s Circuit judge is elected by %s, and the "
                                 "circuit is %s" % (CIRCUIT_NAMES[int(c)], sorted(got),
                                                    sorted(maps["circuits"][c])))
            at_large_rows[c].append(row)
            continue
        m = APPEAL_RE.match(desc)
        if not m or not ordinal_ok(m, "c") or not ordinal_ok(m, "d"):
            unknown(APPEAL, row, "not a court of appeal district")
        unit = "%s-%s" % (m.group("c"), m.group("d"))
        if unit not in maps["appeal"]:
            unknown(APPEAL, row, "the map has no district %s" % unit)
        seat, section = appeal_seat(m)
        if seat is None and (m.group("sub") or m.group("es")):
            unknown(APPEAL, row, "both a subdistrict and an election section")
        where = "Court of appeal district %s %s" % (unit, seat or "")
        got = row_parishes(row, fabric, where)
        if section is None and got != maps["appeal"][unit]:
            raise SystemExit("FAIL: %s is elected district-wide by %s, and the map's district "
                             "takes in %s" % (where, sorted(got), sorted(maps["appeal"][unit])))
        if not got <= maps["appeal"][unit]:
            raise SystemExit("FAIL: %s is elected by %s, outside the map's district (%s)"
                             % (where, sorted(got - maps["appeal"][unit]),
                                sorted(maps["appeal"][unit])))
        district_rows.append((unit, seat, section, got, row))

    kept = one_per_seat([((u, s), r) for u, s, _sec, _g, r in district_rows],
                        "Court of appeal district", notes)
    detail = {(u, s): (sec, g) for u, s, sec, g, _r in district_rows}
    by_unit = defaultdict(list)
    for (unit, seat), row in kept.items():
        by_unit[unit].append((seat, row))

    districts = {}
    for unit in sorted(maps["appeal"], key=lambda u: tuple(int(x) for x in u.split("-"))):
        rows = sorted(by_unit.get(unit, []), key=lambda sr: seat_order(sr[0]))
        if not rows:
            notes.append("Court of appeal district %s: the list names no judge" % unit)
            continue
        members = []
        printed = defaultdict(set)
        for seat, row in rows:
            section, got = detail[(unit, seat)]
            members.append(person(row, "Court of appeal district %s %s" % (unit, seat or ""),
                                  book, notes, seat=seat, section=section))
            if section:
                printed[section] |= got
        rec = {"members": members}
        sections = section_parishes(unit, printed, maps["appeal"][unit], law.get(unit), notes)
        if sections:
            rec["sections"] = sections
        districts[unit] = rec

    circuits = {}
    for c in sorted(maps["circuits"], key=int):
        rows = [r for (u, _s), r in kept.items() if u.split("-")[0] == c] + at_large_rows.get(c, [])
        rec = {}
        if at_large_rows.get(c):
            seen = one_per_seat([((i,), r) for i, r in enumerate(at_large_rows[c])],
                                "the %s Circuit at large" % CIRCUIT_NAMES[int(c)], notes)
            rec["atLarge"] = [person(r, "the %s Circuit at large" % CIRCUIT_NAMES[int(c)], book,
                                     notes, seat="At large") for _k, r in sorted(seen.items())]
        office = office_of(rows, book, "the %s Circuit Court of Appeal" % CIRCUIT_NAMES[int(c)], notes)
        if office:
            rec["office"] = office
        if rec:
            circuits[c] = rec
    return {"districts": districts, "circuits": circuits}


def section_parishes(unit, printed, unit_parishes, law, notes):
    """{section: {"parishes": [...], "whole": [...]}} for a district whose
    judges include some elected from a section. `whole` (the district's
    parishes that lie wholly in that section) is recorded only where the law
    names the district's sections, the list names a judge for each, and the
    parishes each section's judges print are the parishes the law names for
    it; anywhere else the card says only that the sections are not drawn."""
    if not printed:
        return None
    out = {s: {"parishes": sorted(p)} for s, p in sorted(printed.items())}
    if len(unit_parishes) < 2:
        return out
    if not law:
        notes.append("Court of appeal district %s: the list names sections %s, which 13:312 "
                     "does not set; which section a parish is in is not recorded"
                     % (unit, sorted(printed)))
        return out
    want = {"Election Section %d" % n for n in law}
    if set(printed) != want:
        notes.append("Court of appeal district %s: the list names judges for %s of 13:312's %s; "
                     "which section a parish is in is not recorded"
                     % (unit, sorted(printed), sorted(want)))
        return out
    for n, (whole, part) in law.items():
        label = "Election Section %d" % n
        if (whole | part) != printed[label]:
            raise SystemExit("FAIL: 13:312's %s of district %s takes in %s, and the list's judges "
                             "for it are elected by %s" % (label, unit, sorted(whole | part),
                                                          sorted(printed[label])))
    for n, (whole, part) in law.items():
        label = "Election Section %d" % n
        others = set()
        for m, (w2, p2) in law.items():
            if m != n:
                others |= w2 | p2
        # The law's whole/part and the list's overlap must say the same thing.
        if whole != printed[label] - others or part != printed[label] & others:
            raise SystemExit("FAIL: 13:312 puts %s wholly in %s of district %s, and the list's "
                             "sections say %s" % (sorted(whole), label, unit,
                                                  sorted(printed[label] - others)))
        out[label]["whole"] = sorted(whole)
    covered = set()
    for (whole, part) in law.values():
        covered |= whole | part
    if covered != unit_parishes:
        raise SystemExit("FAIL: 13:312's sections of district %s take in %s, and the district is %s"
                         % (unit, sorted(covered), sorted(unit_parishes)))
    return out


def seat_order(seat):
    """At large first, then by section, then by division letter."""
    s = seat or ""
    m = re.search(r"(?:Election Section|Subdistrict) (\d+)", s)
    d = re.search(r"Division ([A-Z])", s)
    return (1 if m else 0, int(m.group(1)) if m else 0, d.group(1) if d else "", s)


def build_district(texts, maps, fabric, book, notes):
    entries = []
    for row in parish.rows_of(texts[DISTRICT], DISTRICT):
        title, desc = row["OfficeTitle"], write_out(row["OfficeTitleDescription"])
        raw = (title, parish.tidy(row["OfficeTitleDescription"]))
        if raw in MAGISTRATES:
            unit, court = MAGISTRATES[raw]
            entries.append((unit, court, None, None, title, row))
            continue
        orleans = None
        for court, pattern in ORLEANS_SEATS.items():
            m = pattern.match(desc)
            if m:
                orleans = (court, m.group("seat"))
        if orleans:
            if title != ORLEANS_TITLE:
                unknown(DISTRICT, row, "an Orleans court's judge not titled %r" % ORLEANS_TITLE)
            entries.append((ORLEANS, orleans[0], orleans[1], None, None, row))
            continue
        m = DISTRICT_RE.match(desc)
        if title != DISTRICT_TITLE or not m or not ordinal_ok(m, "n"):
            unknown(DISTRICT, row, "not a judicial district")
        unit = m.group("n")
        if unit not in maps["district"]:
            unknown(DISTRICT, row, "the map has no %s Judicial District" % unit)
        section = ("Election Section %s" % m.group("es") if m.group("es") else
                   "Subdistrict %s" % m.group("sub") if m.group("sub") else None)
        seat = ", ".join(x for x in (section, m.group("div") and "Division " + m.group("div")) if x)
        entries.append((unit, None, seat or None, section, None, row))

    kept = one_per_seat([((u, c, s, t), r) for u, c, s, _sec, t, r in entries],
                        "Judicial district", notes)
    sections = {(u, c, s, t): sec for u, c, s, sec, t, _r in entries}
    by_unit = defaultdict(list)
    for (unit, court, seat, title), row in kept.items():
        where = "%s %s" % (unit if unit == ORLEANS else "Judicial district " + unit,
                           " ".join(x for x in (court, seat, title) if x))
        got = row_parishes(row, fabric, where)
        section = sections[(unit, court, seat, title)]
        if section is None and got != maps["district"][unit]:
            raise SystemExit("FAIL: %s is elected district-wide by %s, and the map's district "
                             "takes in %s" % (where, sorted(got), sorted(maps["district"][unit])))
        if not got <= maps["district"][unit]:
            raise SystemExit("FAIL: %s is elected by %s, outside the map's district (%s)"
                             % (where, sorted(got - maps["district"][unit]),
                                sorted(maps["district"][unit])))
        rec = person(row, where, book, notes, seat=seat, section=section,
                     title=title, court=court)
        by_unit[unit].append((court, seat_order(seat), rec, row))

    districts = {}
    for unit in sorted(maps["district"], key=lambda u: (u == ORLEANS, int(u) if u.isdigit() else 0)):
        got = sorted(by_unit.get(unit, []), key=lambda x: (x[0] or "", "title" in x[2], x[1]))
        if not got:
            notes.append("Judicial district %s: the list names no judge" % unit)
            continue
        if unit == ORLEANS:
            rec = {"courts": []}
            for court in (CIVIL, CRIMINAL):
                mine = [(r, row) for c, _o, r, row in got if c == court]
                if not mine:
                    notes.append("Orleans Parish: the list names no judge of the %s" % court)
                    continue
                block = {"court": court, "members": [dict((k, v) for k, v in r.items() if k != "court")
                                                     for r, _row in mine]}
                office = office_of([row for _r, row in mine], book, "the Orleans " + court, notes)
                if office:
                    block["office"] = office
                rec["courts"].append(block)
        else:
            rec = {"members": [r for _c, _o, r, _row in got]}
            office = office_of([row for _c, _o, _r, row in got], book,
                               "the %s Judicial District Court" % unit, notes)
            if office:
                rec["office"] = office
        districts[unit] = rec
    return {"districts": districts}


def office_of(rows, book, where, notes):
    address, phone = parish.office_contacts(rows, book, where, notes)
    rec = {}
    if address:
        rec["address"] = address
    if phone:
        rec["phone"] = phone
    return rec or None


# ---------------------------------------------------------------- build

def build(texts, previous, today):
    notes = []
    maps = load_maps()
    fabric = fabric_by_fold()
    law = law_sections(fabric)
    book = parish.contact_book(texts)
    result = {
        "supreme": build_supreme(texts, maps, fabric, book, notes),
        "appeal": build_appeal(texts, maps, fabric, book, law, notes),
        "district": build_district(texts, maps, fabric, book, notes),
        "source": SOURCE,
        "sourceUrl": INDEX_URL,
    }
    read = today
    if isinstance(previous, dict) and previous.get("read"):
        if {k: v for k, v in previous.items() if k != "read"} == result:
            read = previous["read"]
    result["read"] = read
    return result, notes


# ---------------------------------------------------------------- gates

TOP = {"supreme", "appeal", "district", "source", "sourceUrl", "read"}
PERSON = {"seat", "section", "title", "name", "party", "phone", "termEnds"}
OFFICE = {"address", "phone"}
ISO = re.compile(r"\d{4}-\d{2}-\d{2}")


def everyone(data):
    """(court, unit, person) for every judge the file names."""
    out = []
    for unit, rec in (data.get("supreme") or {}).get("districts", {}).items():
        out += [("supreme", unit, p) for p in rec.get("members") or []]
    appeal = data.get("appeal") or {}
    for unit, rec in appeal.get("districts", {}).items():
        out += [("appeal", unit, p) for p in rec.get("members") or []]
    for c, rec in appeal.get("circuits", {}).items():
        out += [("appeal", "circuit " + c, p) for p in rec.get("atLarge") or []]
    for unit, rec in (data.get("district") or {}).get("districts", {}).items():
        out += [("district", unit, p) for p in rec.get("members") or []]
        for block in rec.get("courts") or []:
            out += [("district", unit, p) for p in block.get("members") or []]
    return out


def check_office(rec, where, problems):
    if rec is None:
        return
    if set(rec) - OFFICE or not rec:
        problems.append("%s: office carries %s" % (where, sorted(rec)))
    if rec.get("phone") and (not parish.PHONE_RE.match(rec["phone"]) or
                             parish.placeholder_phone(rec["phone"])):
        problems.append("%s: office telephone %r" % (where, rec["phone"]))


def check_shape(data):
    problems = []
    maps = load_maps()
    if set(data) != TOP:
        problems.append("top-level keys %s" % sorted(data))
    if not ISO.fullmatch(str(data.get("read") or "")):
        problems.append("read %r" % data.get("read"))
    sup = (data.get("supreme") or {}).get("districts", {})
    if set(sup) - set(maps["supreme"]):
        problems.append("Supreme Court districts the map does not draw: %s"
                        % sorted(set(sup) - set(maps["supreme"])))
    for unit, rec in sup.items():
        if len(rec.get("members") or []) != 1:
            problems.append("Supreme Court District %s names %d justices"
                            % (unit, len(rec.get("members") or [])))
    check_office((data.get("supreme") or {}).get("office"), "the Supreme Court", problems)
    appeal = data.get("appeal") or {}
    if set(appeal.get("districts", {})) - set(maps["appeal"]):
        problems.append("court of appeal districts the map does not draw: %s"
                        % sorted(set(appeal["districts"]) - set(maps["appeal"])))
    for unit, rec in appeal.get("districts", {}).items():
        sections = {p.get("section") for p in rec.get("members") or []} - {None}
        if set(rec.get("sections") or {}) != sections:
            problems.append("district %s: sections %s, its judges' %s"
                            % (unit, sorted(rec.get("sections") or {}), sorted(sections)))
        for label, s in (rec.get("sections") or {}).items():
            if not set(s.get("parishes") or []) <= maps["appeal"][unit]:
                problems.append("district %s %s: parishes outside the district" % (unit, label))
            if not set(s.get("whole") or []) <= set(s.get("parishes") or []):
                problems.append("district %s %s: a whole parish it does not list" % (unit, label))
            if set(s) - {"parishes", "whole"}:
                problems.append("district %s %s carries %s" % (unit, label, sorted(s)))
    for c, rec in appeal.get("circuits", {}).items():
        if c not in maps["circuits"]:
            problems.append("circuit %s is not drawn" % c)
        check_office(rec.get("office"), "circuit " + c, problems)
    dist = (data.get("district") or {}).get("districts", {})
    if set(dist) - set(maps["district"]):
        problems.append("judicial districts the map does not draw: %s"
                        % sorted(set(dist) - set(maps["district"])))
    for unit, rec in dist.items():
        check_office(rec.get("office"), "district " + unit, problems)
        for block in rec.get("courts") or []:
            if block.get("court") not in (CIVIL, CRIMINAL) or unit != ORLEANS:
                problems.append("district %s carries a court %r" % (unit, block.get("court")))
            check_office(block.get("office"), "%s %s" % (unit, block.get("court")), problems)
    counts = defaultdict(int)
    phones = parties = 0
    people = everyone(data)
    for court, unit, p in people:
        where = "%s %s" % (court, unit)
        counts[court] += 1
        if set(p) - PERSON:
            problems.append("%s: a judge carries %s" % (where, sorted(set(p) - PERSON)))
        if not parish.readable_name(p.get("name")):
            problems.append("%s: a judge with no readable name" % where)
        if p.get("section") and not str(p.get("seat") or "").startswith(p["section"]):
            problems.append("%s: section %r outside seat %r" % (where, p["section"], p.get("seat")))
        if p.get("phone") and (not parish.PHONE_RE.match(p["phone"]) or
                               parish.placeholder_phone(p["phone"])):
            problems.append("%s: telephone %r" % (where, p["phone"]))
        if p.get("termEnds") and not ISO.fullmatch(p["termEnds"]):
            problems.append("%s: term %r" % (where, p["termEnds"]))
        phones += bool(p.get("phone"))
        parties += bool(p.get("party"))
    if parish.shared_own_phones([p for _c, _u, p in people]):
        problems.append("one telephone rides two judges' rows")
    for court, floor in (("supreme", MIN_JUSTICES), ("appeal", MIN_APPEAL),
                         ("district", MIN_DISTRICT)):
        if counts[court] < floor:
            problems.append("%d %s judges, floor %d" % (counts[court], court, floor))
    n = len(people)
    if n and parties / n < MIN_PARTY_SHARE:
        problems.append("%d of %d judges carry a party, under %.0f%%"
                        % (parties, n, 100 * MIN_PARTY_SHARE))
    if n and phones / n < MIN_PHONE_SHARE:
        problems.append("%d of %d judges carry their own telephone, under %.0f%%"
                        % (phones, n, 100 * MIN_PHONE_SHARE))
    return problems, counts, phones


def summary(data, counts, phones):
    whole = sum(1 for rec in data["appeal"]["districts"].values()
                for s in (rec.get("sections") or {}).values() if s.get("whole") is not None)
    return ("%d justices, %d court of appeal judges and %d district court judges and "
            "magistrates (%d with their own telephone); %d election sections whose whole "
            "parishes are recorded" % (counts["supreme"], counts["appeal"], counts["district"],
                                       phones, whole))


def main(argv):
    args = list(argv)

    def value(flag):
        return args[args.index(flag) + 1] if flag in args else None

    if "--check" in args:
        with open(OUT) as fh:
            data = json.load(fh)
        problems, counts, phones = check_shape(data)
        if problems:
            for p in problems:
                print("FAIL: " + p)
            return 1
        print("OK: %s — %s" % (os.path.relpath(OUT, REPO), summary(data, counts, phones)))
        return 0
    offline, exports, save = value("--offline"), value("--exports"), value("--save")
    kept = offline or exports
    texts = parish.read_exports(offline=kept, save=None if kept else save)
    today = parish.read_date(kept) if kept else datetime.date.today().isoformat()
    try:
        with open(OUT) as fh:
            previous = json.load(fh)
    except (OSError, ValueError):
        previous = {}
    data, notes = build(texts, previous, today)
    problems, counts, phones = check_shape(data)
    if problems:
        for p in problems:
            print("FAIL: " + p)
        return 1
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    print("Wrote %s: %s" % (os.path.relpath(OUT, REPO), summary(data, counts, phones)))
    for n in notes:
        print("  " + n)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
