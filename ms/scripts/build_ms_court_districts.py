#!/usr/bin/env python3
"""
Mississippi Court District Builder (four courts, six files, two of them dated)
==============================================================================
Writes the district maps of the four Mississippi courts whose judges are
elected from districts:

    data/app/ms-supreme-court-districts.json         3 districts
    data/app/ms-court-of-appeals-districts.json      5 districts, with the 10
                                                     counties they split drawn
                                                     on their own (see below)
    data/app/ms-chancery-court-districts.json       20 districts in force until
                                                     1 January 2027
    data/app/ms-circuit-court-districts.json        23 districts in force until
                                                     1 January 2027
    data/app/ms-chancery-court-districts-2027.json  20 districts from that day
    data/app/ms-circuit-court-districts-2027.json   22 districts from that day

EVERY DISTRICT IS A LIST OF COUNTIES, so nothing is drawn but a dissolve of the
county fabric this instance already ships (`state-counties.json`). No map is
read and no publisher is asked at build time: the lists are parsed out of the
copies kept in `data/source/courts/`, whose addresses, fetch dates and SHA-256
hashes are the SOURCES table below, and `--check` recomputes every hash.

WHERE EACH LIST COMES FROM.
  * Supreme Court and Court of Appeals: each court's own district page.
  * Chancery and circuit courts today: each court's own district page, and
    the 2025 laws that redrew both, which must agree with it district by
    district. Senate Bill 2768 rewrote the chancery districts and House Bill
    1544 the circuit districts (both signed 23 April 2025; the Senate's
    summary of that year's judicial redistricting names these two laws and no
    other). Each law writes BOTH maps into the Code at once, in sections that
    read "[Until January 1, 2027, this section shall read as follows:]" and
    "[From and after January 1, 2027, ...]", so the map in force today and the
    map from 1 January 2027 are both the law's own words, and today's half is
    held to the court's page.
  * Two 2026 laws rewrote sections the 2025 laws had written, and are read
    too: House Bill 1 (the Third Chancery District, signed 17 March 2026) and
    House Bill 580 (the Fourth and Seventh Circuit Districts, signed 2 March
    2026). Both changed judgeships and subdistricts and kept every district's
    counties, and a law that writes a district another law also writes must
    give it the same counties on every date, or the build stops for a person
    to decide which reading is right. They were found by reading the short
    title of every measure the Legislature lists for the 2025 and 2026
    regular sessions and both extraordinary sessions (measured 2026-10-15):
    these four are the enacted measures among them that write a chancery or
    circuit district's counties. ms/scripts/validate_sources.py repeats that
    scan monthly, so a later session's law is reported rather than missed.
  * Chancery and circuit courts from 1 January 2027: the "from" half of the
    same sections. Four chancery districts (1, 12, 18 and 20) are in no
    section either law amends, so they keep the counties the court's page
    lists today, and the 2027 map is then held to cover all 82 counties once.

THE COURT OF APPEALS SPLITS TEN COUNTIES BY PRECINCT. Its page names, for each
of Attala, Grenada, Hinds, Jones, Leake, Madison, Montgomery, Panola,
Tallahatchie and Wayne, the precincts that belong to one district, and gives
"that portion ... not included" to another. This app has no map of those
precinct lines (the court's page shows the districts only as a picture,
`coadistrictmap.jpg`), so the line is not drawn: each of the ten is drawn as its
own feature naming BOTH districts and carrying the court's precinct list, and
the card says which district takes the listed precincts and which takes the
rest. Every county must be split exactly once, between exactly two districts,
by one list and one "not included" clause that names the listing district, or
the build stops.

TWO DATES ARE BUILT IN, and both stop the build rather than drift:
  * REDRAW (1 January 2027). The app draws the until-2027 files before that day
    and the 2027 files from it, by the reader's clock. On or after it this
    builder refuses to write the until-2027 files, because they are no longer
    the law, and `--check` says so on every run until they are retired.
  * NEXT_REDRAW (1 January 2031). The same laws already enact a third map
    (George County moves to the Nineteenth Chancery District; Holmes,
    Humphreys and Yazoo leave the Twenty-second Circuit District, which is
    repealed). It is parsed and held to MOVES_2031, which ms/WATCH.md records,
    and never built; the builder refuses to write the 2027 files on or after
    that day.

DO NOT SIMPLIFY AFTER DISSOLVING. The county fabric is already simplified and a
dissolve of it introduces no vertex, so neighbouring districts share their
edges exactly. Simplifying again would move shared edges apart.

Usage:
    python3 build_ms_court_districts.py          # writes the six files (needs shapely)
    python3 build_ms_court_districts.py --check  # offline, stdlib only, verifies them
"""

import argparse
import collections
import datetime
import hashlib
import html
import json
import math
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_INSTANCE = os.path.dirname(_HERE)
SRC = os.path.join(_INSTANCE, "data", "source", "courts")
APP = os.path.join(_INSTANCE, "data", "app")
COUNTIES = os.path.join(APP, "state-counties.json")

REDRAW = datetime.date(2027, 1, 1)
NEXT_REDRAW = datetime.date(2031, 1, 1)

# Every file this builder reads from data/source/courts/, where it was fetched
# from, when, and its SHA-256 as fetched. `--check` recomputes each hash, so a
# copy edited by hand fails rather than parsing into a different map.
SOURCES = {
    "sc-districts.htm": (
        "https://courts.ms.gov/appellatecourts/sc/scdistricts.php", "2026-10-15",
        "1c97fd45dd48a55e3ed7cdbc3536da9b249bd9e2d9d7cd8967dcdfc0dd043799"),
    "coa-districts.htm": (
        "https://courts.ms.gov/appellatecourts/coa/coadistricts.php", "2026-10-15",
        "a247e37e76d198c78ab845c38a683cdd47048bb3dfef680602d0481a79f8f24f"),
    "chancery-districts.htm": (
        "https://courts.ms.gov/trialcourts/chancerycourt/chancerycourt.php",
        "2026-10-15",
        "7ca218ed50f88fc55c46843f7252ff44dc7128823c2dc0beab7d826ae4b6f3de"),
    "circuit-districts.htm": (
        "https://courts.ms.gov/trialcourts/circuitcourt/circuitcourt.php",
        "2026-10-15",
        "81d91495fc32c3a95cd13b1cf78e960116b30588301e2c85d5898edaca47733d"),
    "SB2768SG.htm": (
        "https://billstatus.ls.state.ms.us/documents/2025/html/SB/2700-2799/SB2768SG.htm",
        "2026-10-15",
        "520ebb82364c1e3be0f1daeb31a7b318ac423c2277104ff718aae90bb89d0f6b"),
    "HB1544SG.htm": (
        "https://billstatus.ls.state.ms.us/documents/2025/html/HB/1500-1599/HB1544SG.htm",
        "2026-10-15",
        "181aae668469c9404d17ad97900f40114f21710c3d2154a8e2a8f82b30a347f6"),
    "HB0001SG.htm": (
        "https://billstatus.ls.state.ms.us/documents/2026/html/HB/0001-0099/HB0001SG.htm",
        "2026-10-15",
        "fe27447410a8bc1c5d2026a4db416989b42082750d0bac5388c40d374cc523ac"),
    "HB0580SG.htm": (
        "https://billstatus.ls.state.ms.us/documents/2026/html/HB/0500-0599/HB0580SG.htm",
        "2026-10-15",
        "4546802b26fe90126329d67e6a78d9a8135bbc95e144fe04b9b2b78cc798da49"),
}

# (bill file, how a reader would name it), in enactment order. A law that
# writes a district another law also writes must give it the same counties
# on every date.
BILLS = (
    ("SB2768SG.htm", "Senate Bill 2768 (2025)"),
    ("HB1544SG.htm", "House Bill 1544 (2025)"),
    ("HB0580SG.htm", "House Bill 580 (2026)"),
    ("HB0001SG.htm", "House Bill 1 (2026)"),
)

# (court key, page file, output today, output 2027, units today, units 2027,
#  units 2031, Code chapter)
TRIAL = (
    ("chancery", "chancery-districts.htm", "ms-chancery-court-districts.json",
     "ms-chancery-court-districts-2027.json", 20, 20, 20, "9-5-"),
    ("circuit", "circuit-districts.htm", "ms-circuit-court-districts.json",
     "ms-circuit-court-districts-2027.json", 23, 22, 21, "9-7-"),
)
SC_OUT = "ms-supreme-court-districts.json"
COA_OUT = "ms-court-of-appeals-districts.json"

# The counties each law moves on 1 January 2027, as ms/WATCH.md records them:
# {county: (district until then, district from then)}. A re-parse that moves
# a different set fails, so the record cannot drift from the law's text.
MOVES_2027 = {
    "chancery": {
        "Adams": (17, 4), "Carroll": (6, 3), "Claiborne": (17, 15),
        "Covington": (13, 2), "DeSoto": (3, 17), "Forrest": (10, 13),
        "Greene": (16, 19), "Jefferson": (17, 4), "Jefferson Davis": (13, 2),
        "Lawrence": (13, 15), "Perry": (10, 13), "Simpson": (13, 2),
        "Smith": (13, 2), "Stone": (8, 13), "Sunflower": (9, 7),
        "Tallahatchie": (7, 3), "Walthall": (4, 10), "Webster": (14, 6),
        "Wilkinson": (17, 4),
    },
    "circuit": {
        "Claiborne": (23, 7), "Copiah": (23, 14), "George": (19, 18),
        "Greene": (19, 18), "Jefferson": (23, 7), "Jefferson Davis": (15, 14),
        "Lawrence": (15, 14), "Pike": (14, 6), "Walthall": (14, 15),
        "Wayne": (10, 18),
    },
}
# And on 1 January 2031, from the 2027 map.
MOVES_2031 = {
    "chancery": {"George": (16, 19)},
    "circuit": {"Holmes": (22, 4), "Humphreys": (22, 4), "Yazoo": (22, 9)},
}

ORD = ("First Second Third Fourth Fifth Sixth Seventh Eighth Ninth Tenth "
       "Eleventh Twelfth Thirteenth Fourteenth Fifteenth Sixteenth Seventeenth "
       "Eighteenth Nineteenth Twentieth").split()

EARTH_KM = 6371.0088


def fail(msg):
    print("build-ms-court-districts: FAIL — " + msg)
    sys.exit(1)


def say(msg):
    print("build-ms-court-districts: " + msg)


def ordinal(word):
    """'Twenty-third' -> 23. Raises on anything it does not recognise."""
    w = word.replace("‑", "-").replace("‐", "-")
    if w in ORD:
        return ORD.index(w) + 1
    if w.startswith("Twenty-") and w.split("-", 1)[1].capitalize() in ORD:
        return 20 + ORD.index(w.split("-", 1)[1].capitalize()) + 1
    raise ValueError("unrecognised ordinal word %r" % word)


def utc_today():
    return datetime.datetime.now(datetime.timezone.utc).date()


def read_source(name):
    path = os.path.join(SRC, name)
    if not os.path.exists(path):
        fail("data/source/courts/%s is missing" % name)
    with open(path, "rb") as fh:
        raw = fh.read()
    want = SOURCES[name][2]
    got = hashlib.sha256(raw).hexdigest()
    if got != want:
        fail("data/source/courts/%s hashes %s and SOURCES records %s. The copy "
             "kept here is the record of what was read; if the page was "
             "re-fetched on purpose, record the new hash and date." % (name, got, want))
    return decode_source(raw)


def decode_source(raw):
    """The bills declare windows-1252; the court pages declare nothing and are
    read as UTF-8."""
    m = re.search(rb"charset=([A-Za-z0-9_-]+)", raw[:2048])
    return raw.decode(m.group(1).decode("ascii") if m else "utf-8", errors="replace")


# ---------------------------------------------------------------- counties --

def county_geometry():
    """{BASENAME: geometry} from the shipped county fabric."""
    with open(COUNTIES) as fh:
        feats = json.load(fh)["features"]
    out = {}
    for f in feats:
        name = (f.get("properties") or {}).get("BASENAME")
        if not name:
            fail("a county feature carries no BASENAME")
        if name in out:
            fail("%s appears twice in the county fabric" % name)
        out[name] = f["geometry"]
    if len(out) != 82:
        fail("the county fabric carries %d counties, and Mississippi has 82" % len(out))
    return out


def _key(name):
    return re.sub(r"[^a-z]", "", name.lower())


def resolver(counties):
    """A function mapping a published spelling ("Desoto", "LeFlore") to the
    fabric's BASENAME. Only case, spaces and punctuation are forgiven."""
    table = {_key(n): n for n in counties}

    def resolve(name, where):
        hit = table.get(_key(name))
        if hit is None:
            fail("%s names %r, which is not a Mississippi county in the fabric"
                 % (where, name))
        return hit
    return resolve


def split_list(text):
    """'A, B, C and D' (or 'A, B, and C') -> ['A', 'B', 'C', 'D']."""
    text = re.sub(r"\s+", " ", text).strip().rstrip(".")
    return [p.strip() for p in re.split(r",|\band\b", text) if p.strip()]


# ------------------------------------------------------------ court pages --

def page_lines(raw):
    """A court page as lines of visible text."""
    s = re.sub(r"(?s)<!--.*?-->", " ", raw)
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", s)
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r"(?i)</(p|div|h[1-6]|li|tr|td|th|table|section)>", "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s).replace("\xa0", " ")
    return [" ".join(line.split()) for line in s.split("\n") if line.strip()]


def _once(found, what):
    """{n: [text, ...]} -> {n: text}, where every copy of one district must
    read the same (the Court of Appeals page prints its list twice)."""
    out = {}
    for n, texts in found.items():
        if len(set(texts)) != 1:
            fail("%s prints district %d %d ways: %r" % (what, n, len(set(texts)), texts))
        out[n] = texts[0]
    return out


def headed_lists(lines, heading, what):
    """{n: the 'Counties: ...' text under each '<heading> n' line}."""
    found = collections.defaultdict(list)
    for i, line in enumerate(lines):
        m = re.match(r"^" + re.escape(heading) + r" (\d+)$", line)
        if not m:
            continue
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if not nxt.startswith("Counties:"):
            fail("%s: %r is not followed by a 'Counties:' line" % (what, line))
        found[int(m.group(1))].append(nxt[len("Counties:"):].strip())
    return _once(found, what)


def parse_supreme(resolve, raw=None):
    lines = page_lines(read_source("sc-districts.htm") if raw is None else raw)
    texts = headed_lists(lines, "Supreme Court District", "the Supreme Court's district page")
    if sorted(texts) != [1, 2, 3]:
        fail("the Supreme Court's page lists districts %r, and the court has three"
             % sorted(texts))
    return {n: sorted(resolve(c, "the Supreme Court's page") for c in split_list(t))
            for n, t in texts.items()}


def parse_trial(page, word, resolve, raw=None):
    """{n: [county, ...]} from a trial court's 'District n A, B, C' lines."""
    lines = page_lines(read_source(page) if raw is None else raw)
    found = collections.defaultdict(list)
    for line in lines:
        m = re.match(r"^District (\d+) (.+)$", line)
        if m:
            found[int(m.group(1))].append(m.group(2))
    texts = _once(found, "the %s Court's district page" % word)
    where = "the %s Court's page" % word
    return {n: sorted(resolve(c, where) for c in split_list(t)) for n, t in texts.items()}


APPEALS_PRECINCTS = re.compile(r"^in (.+?) County (.+)$")
APPEALS_REST = re.compile(r"^that portion of (.+?) County not included in the "
                          r"(\S+) Court of Appeals District$")


def parse_appeals(resolve, raw=None):
    """(whole, splits): whole = {n: [county, ...]} of the counties a district
    takes entire; splits = {county: {"named": n, "rest": m, "precincts": text}}."""
    lines = page_lines(read_source("coa-districts.htm") if raw is None else raw)
    what = "the Court of Appeals' district page"
    texts = headed_lists(lines, "Court of Appeals District", what)
    if sorted(texts) != [1, 2, 3, 4, 5]:
        fail("%s lists districts %r, and the court has five" % (what, sorted(texts)))
    whole, named, rest = {}, collections.defaultdict(list), collections.defaultdict(list)
    for n, text in sorted(texts.items()):
        clauses = [c.strip() for c in text.rstrip(".").split(";")]
        whole[n] = sorted(resolve(c, what) for c in split_list(clauses[0]))
        for clause in clauses[1:]:
            clause = re.sub(r"^and\s+", "", clause)
            m = APPEALS_PRECINCTS.match(clause)
            r = APPEALS_REST.match(clause)
            if m and not r:
                named[resolve(m.group(1), what)].append((n, m.group(2)))
            elif r:
                try:
                    other = ordinal(r.group(2))
                except ValueError as exc:
                    fail("%s, district %d: %s" % (what, n, exc))
                rest[resolve(r.group(1), what)].append((n, other))
            else:
                fail("%s, district %d: could not read the clause %r" % (what, n, clause))
    splits = {}
    for county in sorted(set(named) | set(rest)):
        if len(named[county]) != 1 or len(rest[county]) != 1:
            fail("%s: %s County should be split by exactly one precinct list and "
                 "one 'not included' clause; it has %d and %d"
                 % (what, county, len(named[county]), len(rest[county])))
        (a, precincts), (b, other) = named[county][0], rest[county][0]
        if other != a or a == b:
            fail("%s: the rest of %s County goes to district %d as the part 'not "
                 "included in' district %d, but district %d is the one that lists "
                 "its precincts" % (what, county, b, other, a))
        splits[county] = {"named": a, "rest": b, "precincts": precincts}
    return whole, splits


# The four court pages, each with the layer it draws, for the monthly question
# below.
PAGES = {
    "sc-districts.htm": "ms-supreme-court",
    "coa-districts.htm": "ms-court-of-appeals",
    "chancery-districts.htm": "ms-chancery-court",
    "circuit-districts.htm": "ms-circuit-court",
}


def page_parse(name, resolve, raw=None):
    """{"districts": {n: [county, ...]}, "splits": {...}} for one court page,
    the copy kept here when `raw` is None."""
    if name == "sc-districts.htm":
        return {"districts": parse_supreme(resolve, raw), "splits": {}}
    if name == "coa-districts.htm":
        whole, splits = parse_appeals(resolve, raw)
        return {"districts": whole, "splits": splits}
    for court, page, *_rest in TRIAL:
        if page == name:
            return {"districts": parse_trial(page, court.capitalize(), resolve, raw),
                    "splits": {}}
    fail("%s is not one of the court pages this builder reads" % name)


def page_changes(name, live_raw):
    """[difference, ...] between a court page as it is served now (its bytes)
    and the copy kept in data/source/courts/, in the parse the maps were drawn
    from. ms/scripts/validate_sources.py asks this monthly. A page that no
    longer parses fails, as a rebuild from it would."""
    resolve = resolver(county_geometry())
    kept = page_parse(name, resolve)
    live = page_parse(name, resolve, decode_source(live_raw))
    out = []
    for n in sorted(set(kept["districts"]) | set(live["districts"])):
        a, b = kept["districts"].get(n), live["districts"].get(n)
        if a != b:
            out.append("district %d lists %s where the copy of %s lists %s"
                       % (n, ", ".join(b) if b else "nothing", SOURCES[name][1],
                          ", ".join(a) if a else "nothing"))
    for county in sorted(set(kept["splits"]) | set(live["splits"])):
        a, b = kept["splits"].get(county), live["splits"].get(county)
        if a != b:
            out.append("%s County is split %r where the copy of %s splits it %r"
                       % (county, b, SOURCES[name][1], a))
    return out


# -------------------------------------------------------------------- laws --

HEADER = re.compile(r"\[\s*(Until|From and after|From) ([A-Z][a-z]+ \d{1,2}, \d{4})"
                    r"(?:,? (?:and )?until ([A-Z][a-z]+ \d{1,2}, \d{4}))?,? this "
                    r"section shall read as follows:\]")
COMPOSITION = re.compile(
    r"The\s+([A-Z][a-z]+(?:-[a-z]+)?)\s+(?:(Chancery|Circuit)\s+)?Court\s+District"
    r"\s+(?:is|shall be)\s+(?!divided)(?:composed\s+of\s+(?:the following counties:)?)?"
    r"(.*?)(?:\.\s|\(2\)|$)", re.S)
COUNTY_WORD = re.compile(r"([A-Z][A-Za-z]+(?: [A-Z][A-Za-z]+)?) County")


def law_text(raw):
    """The law as enacted: struck words dropped (the bill marks them <s>),
    inserted words kept, hidden spans dropped."""
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
    s = re.sub(r"(?s)<!--.*?-->", " ", s)
    s = re.sub(r"(?is)<s>.*?</s>", " ", s)
    s = re.sub(r"(?is)<span style='[^']*display:none[^']*'>.*?</span>", " ", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s).replace("\xa0", " ").replace("�", " ")
    s = s.replace("* * *", " ").replace("‑", "-")
    return " ".join(s.split())


def _date(text):
    return datetime.datetime.strptime(text, "%B %d, %Y").date()


def law_sections(raw):
    """[(code, [(start, end, chunk), ...])] for every Code section a bill
    amends. A chunk's interval is [start, end); None is open."""
    text = law_text(raw)
    out = []
    parts = re.split(r"SECTION\s+\d+\.", text)
    for part in parts[1:]:
        m = re.match(r"\s*Section\s+(\d+-\d+-\d+),\s*Mississippi Code of 1972", part)
        if not m:
            continue
        code, body = m.group(1), part[m.end():]
        heads = list(HEADER.finditer(body))
        if not heads:
            out.append((code, [(None, None, body)]))
            continue
        chunks = []
        for j, h in enumerate(heads):
            end = heads[j + 1].start() if j + 1 < len(heads) else len(body)
            kind, d1, d2 = h.group(1), _date(h.group(2)), h.group(3)
            if kind == "Until":
                start, stop = None, d1
            else:
                start, stop = d1, (_date(d2) if d2 else None)
            chunks.append((start, stop, body[h.end():end]))
        out.append((code, chunks))
    return out


def composition_of(chunk, code, where):
    """(n, counties) for a chunk that defines a district, ('repealed', date)
    for one that repeals its own section, or None."""
    rep = re.search(r"Section\s+" + re.escape(code) + r"\b[^.]*?shall stand repealed "
                    r"on and after ([A-Z][a-z]+ \d{1,2}, \d{4})", chunk)
    if rep:
        return ("repealed", _date(rep.group(1)))
    hits = list(COMPOSITION.finditer(chunk))
    if not hits:
        return None
    if len(hits) > 1:
        fail("%s § %s: one version of the section defines %d districts"
             % (where, code, len(hits)))
    m = hits[0]
    court = m.group(2) or ("Chancery" if code.startswith("9-5-") else "Circuit")
    want = "Chancery" if code.startswith("9-5-") else "Circuit"
    if court != want:
        fail("%s § %s names a %s district inside the %s chapter" % (where, code, court, want))
    try:
        n = ordinal(m.group(1))
    except ValueError as exc:
        fail("%s § %s: %s" % (where, code, exc))
    words = m.group(3)
    names = COUNTY_WORD.findall(words)
    if words.count(" County") == 1 and ("," in words or " and " in words):
        # "Claiborne, Hinds and Jefferson County": one noun for a list
        names = split_list(words.split(" County")[0])
    if not names:
        fail("%s § %s: district %d names no county" % (where, code, n))
    return (n, names)


def _at(versions, when):
    """The counties one law's versions give on `when` (None if repealed)."""
    hits = [v[2] for v in versions if (v[0] is None or v[0] <= when)
            and (v[1] is None or when < v[1])]
    return hits[0]


def disagree_on(a, b):
    """The first date on which two laws' versions of one district differ, or
    None. Laws may split their tiers differently (one "until 2031", another
    "until 2027" and "from 2027 until 2031"), so they are compared on every
    date either one names, and on a date before them all."""
    dates = sorted({d for v in a + b for d in v[:2] if d is not None})
    for when in [datetime.date(1900, 1, 1)] + dates:
        if _at(a, when) != _at(b, when):
            return when
    return None


def law_districts(resolve):
    """{court: {n: [(start, end, counties or None, code, bill), ...]}} from the
    bills, every district's versions covering all time exactly once."""
    found = {"chancery": collections.defaultdict(dict), "circuit": collections.defaultdict(dict)}
    for bill, label in BILLS:
        for code, chunks in law_sections(read_source(bill)):
            if not (code.startswith("9-5-") or code.startswith("9-7-")):
                continue
            court = "chancery" if code.startswith("9-5-") else "circuit"
            versions, number = [], None
            for start, stop, chunk in chunks:
                got = composition_of(chunk, code, label)
                if got is None:
                    continue
                if got[0] == "repealed":
                    if got[1] != start:
                        fail("%s § %s repeals itself from %s in a version headed "
                             "from %s" % (label, code, got[1], start))
                    versions.append((start, stop, None))
                else:
                    n, names = got
                    if number is not None and n != number:
                        fail("%s § %s defines district %d in one version and %d in "
                             "another" % (label, code, number, n))
                    number = n
                    versions.append((start, stop, sorted(resolve(c, "%s § %s" % (label, code))
                                                         for c in names)))
            if not versions:
                continue  # a section about judges or staff, not a map
            if number is None:
                fail("%s § %s repeals a district it never defines" % (label, code))
            if len(versions) != len(chunks):
                fail("%s § %s has %d versions and %d of them define or repeal its "
                     "district" % (label, code, len(chunks), len(versions)))
            versions.sort(key=lambda v: (v[0] is not None, v[0] or datetime.date.min))
            if versions[0][0] is not None or versions[-1][1] is not None or any(
                    versions[i][1] != versions[i + 1][0] for i in range(len(versions) - 1)):
                fail("%s § %s: its versions do not cover all time exactly once: %r"
                     % (label, code, [(v[0], v[1]) for v in versions]))
            prior = found[court][number]
            for other_bill, (other_code, other_versions) in prior.items():
                if other_code != code:
                    fail("%s writes district %d of the %s court in § %s and %s in § %s"
                         % (other_bill, number, court, other_code, label, code))
                when = disagree_on(other_versions, versions)
                if when is not None:
                    fail("%s and %s both write district %d of the %s court and give "
                         "it different counties on %s" % (other_bill, label, number,
                                                         court, when))
            prior[label] = (code, versions)
    out = {}
    for court, table in found.items():
        out[court] = {}
        for n, by_bill in table.items():
            # Every law agrees on every date, so the first one's tiers stand
            # for all of them.
            code, versions = list(by_bill.values())[0]
            out[court][n] = [(a, b, c, code, " and ".join(by_bill)) for a, b, c in versions]
    return out


def composition_at(page, law, when):
    """{n: [county, ...]} in force on `when`: the law's own version where a law
    writes the district, the court's page where none does."""
    out = {}
    for n in sorted(set(page) | set(law)):
        if n not in law:
            out[n] = page[n]
            continue
        hits = [v for v in law[n] if (v[0] is None or v[0] <= when)
                and (v[1] is None or when < v[1])]
        if len(hits) != 1:
            fail("district %d has %d versions in force on %s" % (n, len(hits), when))
        if hits[0][2] is not None:
            out[n] = hits[0][2]
    return out


def check_partition(what, table, counties):
    """Every county in exactly one district, and no name the fabric lacks."""
    seen = collections.Counter(c for cs in table.values() for c in cs)
    twice = sorted(c for c, k in seen.items() if k > 1)
    if twice:
        fail("%s puts %s in more than one district, so one piece of ground would "
             "be claimed by two courts" % (what, ", ".join(twice)))
    missing = sorted(set(counties) - set(seen))
    if missing:
        fail("%s leaves out %s, so a reader there would be told no court answers"
             % (what, ", ".join(missing)))


def moves(before, after):
    a = {c: n for n, cs in before.items() for c in cs}
    b = {c: n for n, cs in after.items() for c in cs}
    return {c: (a[c], b[c]) for c in a if a[c] != b[c]}


def tilings(counties):
    """Every map this builder knows, parsed and cross-checked, as
    {(court, tier): {n: [county, ...]}} plus the Court of Appeals' parts."""
    resolve = resolver(counties)
    sc = parse_supreme(resolve)
    check_partition("the Supreme Court's page", sc, counties)
    whole, splits = parse_appeals(resolve)
    coa_all = {n: list(cs) for n, cs in whole.items()}
    for county, s in splits.items():
        coa_all[s["named"]].append(county)
    if any(c in splits for cs in whole.values() for c in cs):
        fail("the Court of Appeals' page gives a county both whole and in part")
    check_partition("the Court of Appeals' page", {
        n: whole[n] + [c for c, s in splits.items() if s["named"] == n] for n in whole}, counties)
    out = {("supreme", "now"): sc}
    law = law_districts(resolve)
    for court, page_file, _o1, _o2, n_now, n_2027, n_2031, _ch in TRIAL:
        word = court.capitalize()
        page = parse_trial(page_file, word, resolve)
        if len(page) != n_now or sorted(page) != list(range(1, n_now + 1)):
            fail("the %s Court's page lists districts %r, expected 1 to %d"
                 % (word, sorted(page), n_now))
        check_partition("the %s Court's page" % word, page, counties)
        today = min(utc_today(), REDRAW - datetime.timedelta(days=1))
        now = composition_at(page, law[court], today)
        for n in sorted(law[court]):
            if now.get(n) != page.get(n):
                fail("the %s Court's page puts %r in district %d, and %s puts %r there "
                     "until 1 January 2027" % (word, page.get(n), n, law[court][n][0][4],
                                               now.get(n)))
        untouched = sorted(set(page) - set(law[court]))
        later = composition_at(page, law[court], REDRAW)
        last = composition_at(page, law[court], NEXT_REDRAW)
        for when, table, want in (("now", now, n_now), ("2027", later, n_2027),
                                  ("2031", last, n_2031)):
            if len(table) != want:
                fail("the %s map %s has %d districts, expected %d"
                     % (court, when, len(table), want))
            check_partition("the %s map %s" % (court, when), table, counties)
        if moves(now, later) != MOVES_2027[court]:
            fail("the %s laws move %r on 1 January 2027, and MOVES_2027 (ms/WATCH.md) "
                 "records %r" % (court, moves(now, later), MOVES_2027[court]))
        if moves(later, last) != MOVES_2031[court]:
            fail("the %s laws move %r on 1 January 2031, and MOVES_2031 (ms/WATCH.md) "
                 "records %r" % (court, moves(later, last), MOVES_2031[court]))
        out[(court, "now")] = now
        out[(court, "2027")] = later
        out[(court, "law")] = {n: law[court][n][0][3] for n in law[court]}
        out[(court, "untouched")] = untouched
    return out, whole, splits


# ---------------------------------------------------------------- measure --

def rings_of(geometry):
    kind = geometry.get("type")
    if kind == "Polygon":
        return list(geometry["coordinates"])
    if kind == "MultiPolygon":
        return [r for part in geometry["coordinates"] for r in part]
    fail("unexpected geometry type %r" % kind)


def ring_area_km2(ring):
    """Signed spherical area, so a hole subtracts and winding decides sign."""
    total = 0.0
    for i in range(len(ring) - 1):
        lon1, lat1 = math.radians(ring[i][0]), math.radians(ring[i][1])
        lon2, lat2 = math.radians(ring[i + 1][0]), math.radians(ring[i + 1][1])
        total += (lon2 - lon1) * (2 + math.sin(lat1) + math.sin(lat2))
    return total * EARTH_KM * EARTH_KM / 2.0


def measure(geometry):
    """Area the way a reader's ground is measured: each polygon's outer ring
    less its holes."""
    kind = geometry.get("type")
    polys = [geometry["coordinates"]] if kind == "Polygon" else geometry["coordinates"]
    total = 0.0
    for poly in polys:
        outer = abs(ring_area_km2(poly[0]))
        total += outer - sum(abs(ring_area_km2(r)) for r in poly[1:])
    return total


def holes(geometry):
    kind = geometry.get("type")
    polys = [geometry["coordinates"]] if kind == "Polygon" else geometry["coordinates"]
    return sum(len(p) - 1 for p in polys)


# ------------------------------------------------------------------ files --

def feature_sets(maps, whole, splits):
    """{file: [(properties, [county, ...]), ...]} — what every file holds."""
    files = {SC_OUT: [({"unit": n, "counties": cs}, cs) for n, cs in sorted(maps[("supreme", "now")].items())]}
    coa = [({"units": [n], "counties": cs}, cs) for n, cs in sorted(whole.items())]
    for county, s in sorted(splits.items()):
        coa.append(({"units": sorted([s["named"], s["rest"]]), "county": county,
                     "named": s["named"], "rest": s["rest"],
                     "precincts": s["precincts"]}, [county]))
    files[COA_OUT] = coa
    for court, _page, out_now, out_2027, _a, _b, _c, _ch in TRIAL:
        law = maps[(court, "law")]
        for out_name, tier in ((out_now, "now"), (out_2027, "2027")):
            rows = []
            for n, cs in sorted(maps[(court, tier)].items()):
                props = {"unit": n, "counties": cs}
                if n in law:
                    props["law"] = "Miss. Code § " + law[n]
                rows.append((props, cs))
            files[out_name] = rows
    return files


def build():
    try:
        from shapely.geometry import mapping, shape
        from shapely.ops import unary_union
    except ImportError:
        fail("the build path needs shapely (pip install -c scripts/requirements.txt "
             "shapely). `--check` is stdlib only.")
    today = utc_today()
    if today >= NEXT_REDRAW:
        fail("it is %s: the 2027 maps stopped being the law on 1 January 2031. "
             "Build the 2031 maps (MOVES_2031) and retire the 2027 files." % today)
    if today >= REDRAW:
        fail("it is %s: the until-2027 chancery and circuit maps are no longer "
             "the law. Retire ms-chancery-court-districts.json and "
             "ms-circuit-court-districts.json (the app has drawn the 2027 files "
             "since 1 January 2027) before rebuilding." % today)
    counties = county_geometry()
    maps, whole, splits = tilings(counties)
    for out_name, rows in feature_sets(maps, whole, splits).items():
        features, worst = [], 0.0
        for props, names in rows:
            parts = [shape(counties[c]) for c in names]
            merged = unary_union(parts) if len(parts) > 1 else parts[0]
            want_area = sum(p.area for p in parts)
            worst = max(worst, abs(merged.area - want_area) / want_area)
            geom = mapping(merged)
            geom = json.loads(json.dumps(geom))  # tuples -> lists
            if holes(geom) > sum(holes(counties[c]) for c in names):
                fail("%s: dissolving %s opened %d hole(s) the counties do not have, "
                     "so the fabric has a gap between neighbouring counties"
                     % (out_name, ", ".join(names),
                        holes(geom) - sum(holes(counties[c]) for c in names)))
            features.append({"type": "Feature", "properties": props, "geometry": geom})
        if worst > 1e-9:
            fail("%s: a dissolve moved ground by %.2e of its own area" % (out_name, worst))
        body = json.dumps({"type": "FeatureCollection", "features": features},
                          separators=(",", ":"))
        with open(os.path.join(APP, out_name), "w") as fh:
            fh.write(body)
        say("wrote %s — %d feature(s), %.1f KB, area drift %.1e"
            % (out_name, len(features), len(body) / 1024.0, worst))


def check():
    for name in SOURCES:
        read_source(name)
    counties = county_geometry()
    maps, whole, splits = tilings(counties)
    for out_name, rows in feature_sets(maps, whole, splits).items():
        full = os.path.join(APP, out_name)
        if not os.path.exists(full):
            fail("%s is missing. Run this builder without --check." % out_name)
        with open(full) as fh:
            shipped = json.load(fh)["features"]
        if len(shipped) != len(rows):
            fail("%s ships %d features and the sources give %d"
                 % (out_name, len(shipped), len(rows)))
        worst = 0.0
        for f, (props, names) in zip(shipped, rows):
            if f.get("properties") != props:
                fail("%s ships %r where the sources give %r"
                     % (out_name, f.get("properties"), props))
            # THE IDENTITY, re-derived from the fabric rather than trusted: the
            # shipped shape covers exactly the ground its own counties do.
            drawn = measure(f["geometry"])
            named = sum(measure(counties[c]) for c in names)
            worst = max(worst, abs(drawn - named) / named)
        if worst > 1e-6:
            fail("%s: a shipped shape differs from its own counties' ground by %.2e "
                 "of its area" % (out_name, worst))
        say("%s — %d feature(s), every county once, area identity within %.1e"
            % (out_name, len(rows), worst))
    for court, *_rest in TRIAL:
        say("%s: %d district(s) are in neither 2025 law and keep the court's own "
            "list in 2027: %s" % (court, len(maps[(court, "untouched")]),
                                  ", ".join(map(str, maps[(court, "untouched")])) or "none"))
    today = utc_today()
    if today >= REDRAW:
        say("WARN — it is %s and the until-2027 chancery and circuit files still "
            "ship. The app has drawn the 2027 files since 1 January 2027; retire "
            "the old ones (ms/WATCH.md)." % today)
    say("OK — 6 file(s) for 4 courts; the Court of Appeals splits %d counties by "
        "precinct; the 1 January 2027 moves match MOVES_2027 and the 1 January "
        "2031 moves match MOVES_2031" % len(splits))


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[1])
    ap.add_argument("--check", action="store_true",
                    help="verify the shipped files, write nothing (stdlib only)")
    args = ap.parse_args()
    if args.check:
        check()
    else:
        build()


if __name__ == "__main__":
    main()
