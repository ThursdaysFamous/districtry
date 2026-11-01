#!/usr/bin/env python3
"""
Georgia's 51 superior court circuits, drawn from whole counties, and each
circuit's judges and district attorney, named from the Secretary of State's
official election results.

    python3 ga/scripts/build_ga_superior_courts.py [--cache DIR] [--as-of DATE]
        reads the results and the court system's directory and writes
        ga/data/app/ga-circuit-officials.json and the record
        ga/data/source/ga-judicial-circuits.source.json
    python3 ga/scripts/build_ga_superior_courts.py --draw [--cache DIR]
        does the same and also draws ga/data/app/ga-judicial-circuits.json
        from the county fabric (needs shapely)
    python3 ga/scripts/build_ga_superior_courts.py --check
        offline, stdlib only: the drawn circuits against the record, and every
        name against the rules below

This is the courts part of step 3 of the Georgia launch plan.

WHICH COUNTIES FORM EACH CIRCUIT, MEASURED 2026-10-30. Every county votes for
its own circuit's judges and district attorney, so a county's ballot names its
circuit, and the newest ballot that carries a court contest in a county decides
which circuit it is in. The ballot of 19 May 2026 places 119 counties in 43
circuits; the other 40 counties are in the eight circuits that had no contest
then (Dublin, Northern, Ocmulgee, Oconee, Ogeechee, South Georgia, Tallapoosa
and Toombs), and the general election of 5 November 2024, when all eight
elected a district attorney, places them. That makes 51 circuits, each county
in one. The Launch plan said the May 2026 ballot lists every county's circuit;
it lists 119. Three changes since the 2024 ballots show why the newest ballot
is read and not a list: Stone Mountain was renamed DeKalb (RENAMED), Carroll
and Heard left Coweta to form West Georgia (SPLITS), and Banks moved from
Piedmont to Mountain. A county moving between two of the eight circuits with
no 2026 contest would not show until their next contest; none is known.

  The contest names are spelled several ways ("Circut", "Chattachoochee",
  "Ogechee", "Judicial Circuit Lookout Mountain", "REP - District Attorney
  Enotah Judicial Circuit", Gwinnett's names in English and Spanish), and
  SPELLING evens them out. A court contest naming a circuit this builder does
  not know stops the build.

  The Council of Superior Court Judges' "Find My Local Superior Court" page
  (georgiasuperiorcourts.org) carries a table of counties and circuits too.
  Read 2026-10-30, it disagrees with the ballots about 18 of the 159 counties,
  among them Columbia, which has been its own circuit since before the 2022
  ballot, and Toombs County, which it puts in the Toombs circuit while Toombs
  County votes in the Middle circuit; so it is not read.

WHO HOLDS EACH OFFICE. The results name the winner of every contest, and a
person is named for the winner of their office's newest contest who has taken
office on the day this runs:

  - Judges are elected without party labels, by the voters of the whole
    circuit, in May of each even year, half the circuit's judgeships at a time,
    so the judges in office are the winners of the two newest May elections
    (WINDOW), each seat named on the ballot for the judge who held it. A
    contest nobody won outright is decided by its June runoff; a seat whose
    runoff the site does not carry says so and names nobody. Winners take
    office on 1 January of the next year (TERM_START), so from the May
    election to that day a seat names its sitting judge as the ballot marks
    them, "(I)" for incumbent, and the winner as elected.
  - A district attorney is elected on a party ballot in November, with a
    December runoff, and takes office on 1 January; a party primary chooses a
    nominee and names nobody. The newest general, runoff or special election
    for the circuit's office names the district attorney.
  - A winner is named for at most four years from the day they took office
    (TERM_YEARS), the cycle the ballots show: the same seats are on the 2022
    and 2026 ballots.
  - Results the site does not mark official are not read.

  What the ballots cannot show is an appointment. The governor fills a judge's
  or a district attorney's vacancy, and a judgeship the legislature adds is
  filled the same way, and the person appointed is on no ballot until the seat
  next is. So a card names the winner of the seat's last election, with its
  date, and says that.

THE COURT SYSTEM'S DIRECTORY IS A CHECK, NOT A SOURCE. The Administrative
Office of the Courts publishes a directory of judges and court officers
(georgiacourts.knack.com/gcd2, linked from georgiacourts.gov's data page),
whose page reads its records from Knack's public api with the application id
it hands every visitor. Read 2026-10-30, it lists 217 superior court judges
and 43 district attorneys by circuit, and it is not current: several of its
district attorneys are the people the November 2024 winners replaced (Cobb,
Houston, Chattahoochee), it still calls DeKalb "Stone Mountain", and it lacks
some judges on the 2024 and 2026 ballots. It also carries no dates, so where
it and the ballots disagree, nothing here says which is newer. It is read for
three things only:

  - A circuit that SPLIT since its judges were elected: Coweta's six 2024
    judgeships now sit in Coweta or West Georgia, which the ballot cannot say,
    and each winner is placed in the circuit the directory lists them in. A
    winner it lists in neither, or in both, stops the build.
  - A person the directory lists in ANOTHER office in the same circuit, which
    is a government record that they left the one the ballot names: a
    district attorney it lists as a superior court judge, or a judge in office
    it lists as a senior judge, which is a retired one, unless it lists them on
    the circuit's bench as well, since a senior judge can share a sitting
    judge's name. That person is not named, and the card says why. The same
    holds without the directory where the ballots themselves name one person
    as a circuit's district attorney and as a judge who has taken office. A
    name matches when the surname is the same and the shorter run of first
    and middle names fits, in order, into the longer (same_person); two
    people whose given names only share an initial in different places are
    not matched.
  - The rest of its disagreements are printed every run for a person to read,
    and change nothing.

WHAT IS NOT READ. sos.ga.gov answers robots.txt with a challenge page and its
voter page (mvp.sos.ga.gov) answered a challenge on 2026-10-30, so neither is
read. The Prosecuting Attorneys' Council's site (pacga.org) permits reading in
its robots.txt, but every page's footer says it is "a restricted website ...
provided for the conduct of official state business only", so it is not read
either.

Usage:
  python3 ga/scripts/build_ga_superior_courts.py [--cache DIR] [--offline] [--as-of DATE] [--draw]
  python3 ga/scripts/build_ga_superior_courts.py --check
"""

import argparse
import datetime
import json
import os
import re
import sys
import unicodedata

_HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE_ROOT = os.path.dirname(_HERE)
ROOT = os.path.dirname(INSTANCE_ROOT)
for _d in (_HERE, os.path.join(ROOT, "scripts")):
    if _d not in sys.path:
        sys.path.insert(0, _d)
import check_ga_county_maps as cmap  # noqa: E402  (same instance: fetching and caching)
import build_ga_county_officials as bco  # noqa: E402  (same instance: reading results)
import whole_county_courts as wcc  # noqa: E402  (FLEET_SHARED)

LABEL = "build-ga-superior-courts"
TAG = "ga"
ROSTER = os.path.join(INSTANCE_ROOT, "data", "app", "ga-circuit-officials.json")
RECORD = os.path.join(INSTANCE_ROOT, "data", "source", "ga-judicial-circuits.source.json")
CIRCUITS_FILE = "ga-judicial-circuits.json"
CIRCUITS = 51
DIRECTORY_PAGE = "https://georgiacourts.knack.com/gcd2/#home/"
DIRECTORY_API = "https://us-api.knack.com/v1/scenes/scene_1/views/view_5/records"
# The application id the directory's page hands every visitor (its HTML sets
# `app_id`), and the key Knack's public views take; page configuration, not a
# credential.
DIRECTORY_APP = "582a4334ad388bdb3448f61a"
DIRECTORY_SECTIONS = {"judge": "Superior Court Judges", "senior": "Senior Judges",
                      "da": "District Attorneys"}
# The oldest election read: the primary of 24 May 2022, before the general
# election that chose the district attorneys whose terms run to the end of 2026.
START = "2022-05-24"
TERM_YEARS = 4
# Judges are elected half at a time, so the two newest May elections hold every
# judgeship a ballot has filled.
WINDOW = 2

# Circuit names as the contests spell them, evened out (lower case).
SPELLING = (("circut", "circuit"), ("chattachoochee", "chattahoochee"),
            ("ogechee", "ogeechee"), ("bell forsyth", "bell-forsyth"))
# A circuit the legislature renamed: the old name's contests are the new one's.
RENAMED = {"stone mountain": "dekalb"}
# A circuit split since a ballot: contests of `circuit` held on or before
# `through` belong to whichever of `into` the court system's directory lists
# each winner in, and the counties of `into` must all have voted in `circuit`'s
# contests on the `through` ballot.
SPLITS = {"coweta": {"through": "2024-11-05", "into": ("coweta", "west georgia")}}
DISPLAY = {"dekalb": "DeKalb"}

PARTY_PREFIX = re.compile(r"^\s*(?:rep|dem|republican|democrat|democratic)\s*-\s*", re.I)
SPECIAL = re.compile(r"\bspecial\b", re.I)
RUNOFF = re.compile(r"\brunoff\b", re.I)


def fail(msg):
    raise SystemExit("%s: FAIL — %s" % (LABEL, msg))


def circuit_name(key):
    """"lookout mountain" -> "Lookout Mountain", "bell-forsyth" -> "Bell-Forsyth"."""
    if key in DISPLAY:
        return DISPLAY[key]
    return " ".join("-".join(p.capitalize() for p in w.split("-")) for w in key.split(" "))


# --------------------------------------------------------------- contests

def parse(name):
    """(kind, circuit, seat, primary) for a superior court judge's or district
    attorney's contest, else None. `seat` is the judge the ballot names the
    seat for, in lower case, or "" for a circuit with one judge."""
    seat = re.search(r"\(([^)]*)\)", name)
    head = name.split("/")[0]
    primary = bool(PARTY_PREFIX.match(head)) or bool(bco.PARTY_TAIL.search(head))
    low = " ".join(PARTY_PREFIX.sub("", head).split()).lower()
    for a, b in SPELLING:
        low = low.replace(a, b)
    if "clerk" in low:
        return None
    if "superior court" in low and re.search(r"\bjudge\b", low):
        kind = "judge"
    elif "district attorney" in low:
        kind = "da"
    else:
        return None
    low = re.sub(r"\([^)]*\)", "", low)
    low = bco.PARTY_TAIL.sub("", low).strip()
    low = re.sub(r"^(?:judge\s*-\s*)?superior court\s*-\s*|^district attorney\s*-?\s*", "", low)
    low = re.sub(r"\b(?:judicial\s+)?circuit\b|\bjudge\b", "", low)
    low = re.sub(r"\s+-\s+.*$", "", low).strip(" -")
    seat = " ".join(seat.group(1).split()).lower() if seat else ""
    return kind, low, seat, primary


def elections(cache):
    """[(id, date, name)] of every election on the site from START on, oldest
    first, recounts left out."""
    page = json.loads(bco.fresh(cache, ("elections.json",), bco.JURISDICTION) or "null")
    if not page:
        fail("%s answered nothing" % bco.JURISDICTION)
    out = []
    for e in page.get("elections") or []:
        day = e.get("electionDate") or ""
        name = cmap.text(e.get("name"))
        if day < START or re.search(r"\brecount\b", name, re.I):
            continue
        out.append((e["publicElectionId"], day[:10], name.strip()))
    return sorted(out, key=lambda x: (x[1], x[0]))


def read_state(cache, el):
    """An election's statewide results: read back once the site marks them
    official, since official results do not change, and fetched otherwise."""
    path = os.path.join(cache, "results", el, "Georgia.json") if cache else None
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        d = json.loads(text) if text else None
        if bco.official(d) or cmap.OFFLINE:
            return d
    return bco.read_state(cache, el)


def candidates(item):
    return [(cmap.text(o["name"]), o.get("voteCount") or 0) for o in
            item["summaryResults"]["ballotOptions"]]


def read_contests(cache, els, known):
    """Every judge's and district attorney's contest from START on that is not
    a party primary, the newest party primary for each circuit's district
    attorney ({circuit: date}), and the elections whose results are not
    official yet."""
    contests, pending, primaries = [], [], {}
    for el, day, label in els:
        state = read_state(cache, el)
        items = [bi for bi in (state or {}).get("ballotItems") or []
                 if bi.get("contestType") == "Candidate"]
        mine = [(bi, cmap.text(bi["name"])) for bi in items if parse(cmap.text(bi["name"]))]
        if not mine:
            continue
        if not bco.official(state):
            pending.append(el)
            continue
        for bi, name in mine:
            kind, circ, seat, primary = parse(name)
            if circ not in known:
                fail("%s %r names a circuit this builder does not know (%r)" % (el, name, circ))
            if primary:
                if kind == "da":
                    primaries[RENAMED.get(circ, circ)] = day
                continue
            runoff = bool(RUNOFF.search(label) or RUNOFF.search(name))
            special = bool(SPECIAL.search(name)) or (bool(SPECIAL.search(label))
                                                     and not re.search(r"general|primary", label, re.I))
            if kind == "judge" and special:
                fail("%s %r is a special election for a judgeship, which this builder "
                     "has not seen and does not read" % (el, name))
            won, votes = bco.winners(bi, runoff)
            if won and won[0] == "contested":
                fail("%s %r elects several, which no court contest did on 2026-10-30" % (el, name))
            sitting = [bco.clean_name(n) for n, _ in candidates(bi) if re.search(r"\(I\)", n)]
            label_seat = re.search(r"\(([^)]*)\)", name)
            contests.append({
                "election": el, "date": day, "electionName": label, "kind": kind,
                "circuit": RENAMED.get(circ, circ), "ballotCircuit": circ, "seat": seat,
                "seatLabel": " ".join(label_seat.group(1).split()) if label_seat else "",
                "runoff": runoff, "special": special, "contest": name,
                "won": [(tidy(n), p) for n, p, _v in won] if won else None,
                "sitting": tidy(sitting[0]) if len(sitting) == 1 else None,
            })
        print("  read %s (%s)" % (el, day), file=sys.stderr, flush=True)
    return contests, pending, primaries


def tidy(name):
    """A candidate's name with the site's doubled quotes made single."""
    s = name.replace("''", '"').replace('""', '"')
    return re.sub(r"\s+", " ", s).strip()


# --------------------------------------------------------------- circuits

def county_keys():
    with open(bco.COUNTIES, encoding="utf-8") as fh:
        fc = json.load(fh)
    return {cmap.county_key(f["properties"]["BASENAME"]): f["properties"]["BASENAME"]
            for f in fc["features"]}


def known_circuits(record=None):
    """Every circuit name a contest may carry: today's, the renamed and the
    split ones. Today's come from the record when one is given."""
    names = set(RENAMED) | set(RENAMED.values()) | set(SPLITS)
    for s in SPLITS.values():
        names |= set(s["into"])
    if record:
        names |= {k for k in record["circuits"]}
    return names


def membership(cache, els):
    """{county BASENAME: {circuit, election, date, contests}} from the newest
    official ballot carrying a court contest in each county. The circuits
    found here are today's; a spelling SPELLING does not even out would show
    as a circuit too many."""
    keys = county_keys()
    placed = {}
    for el, day, _label in sorted(els, key=lambda x: (x[1], x[0]), reverse=True):
        if len(placed) == len(keys):
            break
        state = read_state(cache, el)
        if not bco.official(state) or not any(
                parse(cmap.text(bi["name"])) for bi in state.get("ballotItems") or []):
            continue
        for c in (state.get("jurisdiction") or {}).get("childLocalities") or []:
            sn = c["shortName"]
            ck = cmap.county_key(sn.replace("-county-ga", "").replace("-", " "))
            if ck not in keys:
                fail("%s lists a county %r the county fabric does not carry" % (el, sn))
            if keys[ck] in placed:
                continue
            d = bco.read_county(cache, el, sn)
            if not bco.official(d):
                continue
            seen = {}
            for bi in (d or {}).get("ballotItems") or []:
                p = parse(cmap.text(bi["name"]))
                if p:
                    seen.setdefault(RENAMED.get(p[1], p[1]), []).append(cmap.text(bi["name"]))
            if not seen:
                continue
            if len(seen) > 1:
                fail("%s's ballot of %s carries contests of %s" % (keys[ck], day, sorted(seen)))
            (circ, names), = seen.items()
            placed[keys[ck]] = {"circuit": circ, "election": el, "date": day,
                                "contests": sorted(set(names))}
    missing = sorted(set(keys.values()) - set(placed))
    if missing:
        fail("no official ballot carries a court contest in %s" % ", ".join(missing))
    return placed


def check_splits(cache, els, placed):
    """Each SPLITS entry still describes the ballots: every county of each
    circuit it splits into voted in the old circuit's contests on the
    `through` ballot."""
    by_day = {day: el for el, day, _l in els}
    for old, s in SPLITS.items():
        el = by_day.get(s["through"])
        if not el:
            fail("SPLITS %r: no election on %s" % (old, s["through"]))
        state = read_state(cache, el)
        sns = {cmap.county_key(c["shortName"].replace("-county-ga", "").replace("-", " ")):
               c["shortName"] for c in (state.get("jurisdiction") or {}).get("childLocalities") or []}
        for county, rec in sorted(placed.items()):
            if rec["circuit"] not in s["into"]:
                continue
            d = bco.read_county(cache, el, sns[cmap.county_key(county)])
            circs = {RENAMED.get(p[1], p[1]) for p in (parse(cmap.text(bi["name"])) for bi in
                                                       (d or {}).get("ballotItems") or []) if p}
            if circs != {old}:
                fail("SPLITS %r: %s voted in %s on %s, not only in %r; the entry no longer "
                     "describes the ballots" % (old, county, sorted(circs), s["through"], old))
        if not any(rec["circuit"] == old for rec in placed.values()):
            fail("SPLITS %r: no county is in that circuit today" % old)


# --------------------------------------------------------------- directory

def read_directory(cache):
    """{section: [(circuit key, title, name)]} from the court system's
    directory, read the way its own page reads it."""
    import requests
    from robots_policy import RobotsGate

    path = os.path.join(cache, "directory.json") if cache else None
    if cmap.OFFLINE:
        if not path or not os.path.exists(path):
            fail("--offline and the cache holds no copy of the court directory")
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    s = requests.Session()
    s.headers["User-Agent"] = cmap.USER_AGENT
    gate = RobotsGate(s, cmap.USER_AGENT)
    ok, why = gate.allows(DIRECTORY_API)
    print("robots.txt us-api.knack.com: %s" % why, file=sys.stderr)
    if not ok:
        fail("robots.txt refuses %s (%s)" % (DIRECTORY_API, why))
    out = {}
    for key, section in DIRECTORY_SECTIONS.items():
        rule = {"match": "and", "rules": [{"field": "field_19", "operator": "is", "value": section}]}
        resp = s.get(DIRECTORY_API, timeout=120,
                     params={"page": 1, "rows_per_page": 1000, "filters": json.dumps(rule)},
                     headers={"X-Knack-Application-Id": DIRECTORY_APP,
                              "X-Knack-REST-API-Key": "knack"})
        resp.raise_for_status()
        d = resp.json()
        recs = d.get("records") or []
        if int(d.get("total_records") or 0) != len(recs) or not recs:
            fail("the directory's %s answered %s of %s records"
                 % (section, len(recs), d.get("total_records")))
        rows = []
        for r in recs:
            circ = " ".join((r.get("field_14") or "").split()).lower()
            name = " ".join(" ".join((r.get(f) or "") for f in ("field_1", "field_4", "field_2")).split())
            rows.append([circ, (r.get("field_3") or "").strip(), name])
        out[key] = sorted(rows)
    if path:
        with open(path + ".part", "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=0)
        os.replace(path + ".part", path)
    return out


def name_key(name):
    """(first, last) in plain lower case, with nicknames, initials and suffixes
    left out: "M. Anthony "Tony" Baker" -> ("anthony", "baker")."""
    n = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower()
    n = re.sub(r'"[^"]*"|\([^)]*\)', " ", n)
    n = re.sub(r"\b(?:jr|sr|ii|iii|iv)\b\.?", " ", n)
    toks = [t for t in re.findall(r"[a-z][a-z'\-]*", n) if len(t) > 1]
    if len(toks) < 2:
        return (toks[0] if toks else "", toks[0] if toks else "")
    return toks[0], toks[-1]


def given_names(name):
    """The first and middle names and initials in order, a nickname in quotes
    where it stands: "C. Jephson "Jep" Bendinger" -> ["c", "jephson", "jep"]."""
    n = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower()
    n = re.sub(r"\b(?:jr|sr|ii|iii|iv)\b\.?", " ", n)
    toks = re.findall(r"[a-z][a-z'\-]*", n)
    return toks[:-1]


def _fits(x, y):
    """An initial stands for a name it starts, and a name for one it begins:
    "w" fits "william", "greg" fits "gregory"."""
    if len(x) == 1 or len(y) == 1:
        return x[:1] == y[:1]
    return x.startswith(y) or y.startswith(x)


def same_person(a, b):
    """The same surname, and the shorter run of first and middle names fits,
    in order, into the longer: "W. Travis Sakrison" is "William Travis
    Sakrison" and "Greg Poole" is "A. Gregory Poole", while "D. Scott Smith"
    is not "David K. Smith" and "Nina M. Baker" is not "M. Anthony Baker"."""
    if name_key(a)[1] != name_key(b)[1]:
        return False
    ga, gb = given_names(a), given_names(b)
    if not ga or not gb:
        return False
    short, long_ = (ga, gb) if len(ga) <= len(gb) else (gb, ga)
    i = 0
    for x in short:
        while i < len(long_) and not _fits(x, long_[i]):
            i += 1
        if i == len(long_):
            return False
        i += 1
    return True


def directory_circuit(circ):
    circ = RENAMED.get(circ, circ)
    # One entry spells its circuit as its counties.
    return {"bartow, gordon": "cherokee"}.get(circ, circ)


# --------------------------------------------------------------- holders

def took_office(c):
    return c["date"] if c["special"] else "%d-01-01" % (int(c["date"][:4]) + 1)


def term_end(since):
    return "%d%s" % (int(since[:4]) + TERM_YEARS, since[4:])


def person(c, who, party=None):
    rec = {"name": who}
    if party:
        rec["party"] = party
    rec.update({"elected": c["date"], "election": c["election"],
                "electionName": c["electionName"], "since": took_office(c)})
    if c["special"]:
        rec["special"] = True
    if c.get("placedBy"):
        rec["ballotCircuit"] = circuit_name(c["ballotCircuit"])
    return rec


def place_splits(contests, directory):
    """Put each winner of a split circuit's contest in the circuit the
    directory lists them in."""
    for c in contests:
        s = SPLITS.get(c["ballotCircuit"])
        if not s or c["date"] > s["through"]:
            continue
        if not c["won"]:
            fail("%s %r was a contest of a circuit that has split since, and nobody won it"
                 % (c["election"], c["contest"]))
        section = "judge" if c["kind"] == "judge" else "da"
        hits = sorted({directory_circuit(circ) for circ, _t, n in directory[section]
                       if directory_circuit(circ) in s["into"] and same_person(n, c["won"][0][0])})
        if len(hits) != 1:
            fail("%s %r: the directory lists the winner %s in %s of %s, so this builder cannot "
                 "tell which circuit they sit in" % (c["election"], c["contest"], c["won"][0][0],
                                                     hits or "none", list(s["into"])))
        c["circuit"] = hits[0]
        c["placedBy"] = "directory"


def judges_of(contests, as_of, directory):
    """{circuit: [seat]} from the WINDOW newest May elections."""
    regular = sorted({c["date"][:4] for c in contests if c["kind"] == "judge"})
    years = regular[-WINDOW:]
    seats = {}
    for c in sorted((c for c in contests if c["kind"] == "judge" and c["date"][:4] in years),
                    key=lambda c: (c["date"], c["election"])):
        # A split circuit's seats were named on one ballot for two circuits'
        # judges, so its winners are told apart by name.
        tell = c["won"][0][0] if c.get("placedBy") else c["ballotCircuit"]
        key = (c["circuit"], c["date"][:4], c["seat"], tell)
        prev = seats.get(key)
        if prev and not c["runoff"]:
            fail("%s: two contests for the seat %r in %s" % (c["circuit"], c["seat"], key[1]))
        if prev and prev.get("won") and c["runoff"]:
            fail("%s: a runoff for the seat %r, which its May contest already filled"
                 % (c["circuit"], c["seat"]))
        if prev and c["runoff"]:
            c = dict(c, sitting=prev.get("sitting"))
        seats[key] = c
    senior = [(directory_circuit(circ), n) for circ, _t, n in directory["senior"]]
    bench = [(directory_circuit(circ), n) for circ, _t, n in directory["judge"]]

    def retired(circ, name):
        """The directory's senior judge of this circuit `name` is, unless it
        also lists them on the circuit's bench: a senior judge can share a
        name with a sitting one."""
        if not name or any(bc == circ and same_person(n, name) for bc, n in bench):
            return None
        hits = [n for sc, n in senior if sc == circ and same_person(n, name)]
        return hits[0] if hits else None

    out = {}
    for (circ, year, seat, _x), c in sorted(seats.items()):
        # The seat as the ballot names it, for the judge who held it then.
        rec = {"seat": c["seatLabel"]}
        if not c["won"]:
            rec.update({"name": None, "runoff": True, "contest": c["contest"],
                        "election": c["election"], "electionName": c["electionName"],
                        "elected": c["date"]})
        else:
            who = person(c, c["won"][0][0])
            if who["since"] <= as_of:
                if as_of >= term_end(who["since"]):
                    continue
                gone = retired(circ, who["name"])
                if gone:
                    rec.update({"name": None, "withheld": dict(who, listedAs="senior judge",
                                                              listedName=gone)})
                else:
                    rec.update(who)
            else:
                # Until the winner takes office the seat names the judge the
                # ballot marks as its incumbent.
                rec.update({"name": c.get("sitting"), "elect": who})
                if c.get("sitting"):
                    rec["sittingFrom"] = c["date"]
                    gone = retired(circ, c["sitting"])
                    if gone:
                        rec["name"] = None
                        rec["withheld"] = {"name": rec.pop("sittingFrom") and c["sitting"],
                                           "sittingFrom": c["date"],
                                           "listedAs": "senior judge", "listedName": gone}
        out.setdefault(circ, []).append(rec)
    return out, years


def das_of(contests, as_of, directory, judges):
    """{circuit: record} from each circuit's newest district attorney contest."""
    by = {}
    for c in sorted((c for c in contests if c["kind"] == "da"),
                    key=lambda c: (c["date"], c["election"])):
        by.setdefault(c["circuit"], []).append(c)
    sitting_judges = {}
    for circ, seats in judges.items():
        for s in seats:
            if s.get("name") and s.get("since") and s["since"] <= as_of:
                sitting_judges.setdefault(circ, []).append(s["name"])
    dir_judges = [(directory_circuit(circ), n) for circ, _t, n in directory["judge"]]
    out = {}
    for circ, cs in by.items():
        newest = cs[-1]
        if not newest["won"]:
            out[circ] = {"name": None, "runoff": True, "contest": newest["contest"],
                         "election": newest["election"], "electionName": newest["electionName"],
                         "elected": newest["date"]}
            continue
        current = None
        later = None
        for c in reversed(cs):
            if not c["won"]:
                continue
            who = person(c, c["won"][0][0], c["won"][0][1])
            if who["since"] <= as_of:
                if as_of < term_end(who["since"]):
                    current = who
                break
            later = later or who
        rec = dict(current) if current else {"name": None}
        if later:
            rec["elect"] = later
        if current:
            listed = [n for jc, n in dir_judges if jc == circ and same_person(n, current["name"])]
            bench = [n for n in sitting_judges.get(circ, []) if same_person(n, current["name"])]
            if listed or bench:
                rec = {"name": None, "withheld": dict(current, listedAs="superior court judge",
                                                      listedName=(listed or bench)[0],
                                                      listedBy="directory" if listed else "ballot")}
                if later:
                    rec["elect"] = later
        out[circ] = rec
    return out


def disagreements(judges, das, directory):
    """Lines saying where the directory and the ballots differ, for the log."""
    lines = []
    dirj = {}
    for circ, _t, n in directory["judge"]:
        dirj.setdefault(directory_circuit(circ), []).append(n)
    for circ in sorted(set(judges) | set(dirj)):
        ballot = [s.get("name") or (s.get("elect") or {}).get("name") or
                  (s.get("withheld") or {}).get("name") for s in judges.get(circ, [])]
        ballot = [b for b in ballot if b]
        only_b = [b for b in ballot if not any(same_person(b, d) for d in dirj.get(circ, []))]
        only_d = [d for d in dirj.get(circ, []) if not any(same_person(b, d) for b in ballot)]
        if only_b or only_d:
            lines.append("%s judges: on the ballots only %s; in the directory only %s"
                         % (circuit_name(circ), only_b or "-", only_d or "-"))
    dird = {}
    for circ, _t, n in directory["da"]:
        dird.setdefault(directory_circuit(circ), []).append(n)
    for circ in sorted(set(das) | set(dird)):
        b = (das.get(circ) or {}).get("name")
        d = dird.get(circ) or []
        if not b or not any(same_person(b, x) for x in d):
            lines.append("%s district attorney: the ballots %s; the directory %s"
                         % (circuit_name(circ), b or "name nobody", d or "lists nobody"))
    return lines


# --------------------------------------------------------------- writing

MIN_JUDGES = 200      # 2026-10-30: 221 named or elected, 3 withheld, of 224 on the two ballots
MIN_DAS = 40          # 2026-10-30: 46 named, 4 withheld, West Georgia none yet


def write_json(path, doc):
    with open(path + ".part", "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    os.replace(path + ".part", path)


def counted(judges, das):
    j = sum(1 for seats in judges.values() for s in seats if s.get("name") or s.get("elect"))
    d = sum(1 for r in das.values() if r.get("name"))
    return j, d


def build(args):
    cmap.OFFLINE = args.offline
    cache = os.path.abspath(args.cache) if args.cache else None
    as_of = args.as_of or datetime.date.today().isoformat()
    els = elections(cache)
    placed = membership(cache, els)
    circuits = {}
    for county, rec in placed.items():
        circuits.setdefault(rec["circuit"], []).append(county)
    if len(circuits) != CIRCUITS:
        fail("the ballots place the counties in %d circuits, expected %d" % (len(circuits), CIRCUITS))
    for old, new in RENAMED.items():
        if old in circuits or new not in circuits:
            fail("RENAMED %r -> %r no longer describes the newest ballots" % (old, new))
    check_splits(cache, els, placed)
    directory = read_directory(cache)
    # Every contest read must name one of today's circuits or one RENAMED or
    # SPLITS accounts for, so an older contest spelled a new way stops the
    # build rather than filing its judge under a circuit nobody is in.
    contests, pending, primaries = read_contests(cache, els, set(circuits) | known_circuits())
    place_splits(contests, directory)
    judges, years = judges_of(contests, as_of, directory)
    das = das_of(contests, as_of, directory, judges)

    record = {
        "built": as_of,
        "source": bco.RESULTS_PAGE,
        "directory": DIRECTORY_PAGE,
        "rule": "Each county's circuit is the one whose contests are on its newest official "
                "ballot carrying a court contest.",
        "circuits": {},
    }
    # Keyed by circuit, each record carrying the day it was read, the shape
    # of the county officials' roster.
    roster = {}
    for circ in sorted(circuits):
        cs = sorted(circuits[circ])
        ballots = sorted({(placed[c]["date"], placed[c]["election"]) for c in cs})
        record["circuits"][circuit_name(circ)] = {
            "counties": {c: {"election": placed[c]["election"], "date": placed[c]["date"],
                             "contests": placed[c]["contests"]} for c in cs}}
        seats = sorted(judges.get(circ, []), key=lambda s: (
            name_key(s.get("name") or (s.get("elect") or s.get("withheld") or {}).get("name") or s["seat"])[1],
            s["seat"]))
        da = das.get(circ)
        if not da:
            # No general election has chosen one; a party primary since says
            # one is coming.
            da = {"name": None}
            if primaries.get(circ):
                da["nominated"] = primaries[circ]
        rec = {"asOf": as_of, "judgeElections": years,
               "countiesFrom": [{"election": el, "elected": day} for day, el in ballots],
               "judges": seats, "districtAttorney": da}
        for old, sp in SPLITS.items():
            if circ in sp["into"] and circ != old:
                rec["formedFrom"] = {"circuit": circuit_name(old), "through": sp["through"]}
        if pending:
            rec["pending"] = sorted(pending)
        roster[circuit_name(circ)] = rec
    j, d = counted(judges, das)
    if j < MIN_JUDGES or d < MIN_DAS:
        fail("%d judges and %d district attorneys named, under the floors of %d and %d"
             % (j, d, MIN_JUDGES, MIN_DAS))
    write_json(ROSTER, roster)
    write_json(RECORD, record)
    if args.draw:
        wcc.build(TAG, LABEL, tilings(record))
    else:
        shipped = os.path.join(wcc.app_dir(TAG), CIRCUITS_FILE)
        with open(shipped, encoding="utf-8") as fh:
            drawn = {f["properties"]["unit"]: sorted(f["properties"]["counties"])
                     for f in json.load(fh)["features"]}
        want = {u: sorted(cs) for u, cs, _p in tilings(record)[0].rows}
        if drawn != want:
            moved = sorted(c for u in want for c in want[u] if c not in drawn.get(u, []))
            fail("the newest ballots move %s to another circuit than the drawn map has; "
                 "redraw with --draw and change the app's cache name" % ", ".join(moved))
    withheld = [(circ, s["withheld"]) for circ, seats in judges.items() for s in seats
                if s.get("withheld")] + [(circ, r["withheld"]) for circ, r in das.items()
                                         if r.get("withheld")]
    print("wrote %s as of %s: %d circuits; %d judges named or elected (judges' elections %s), "
          "%d district attorneys named, %d people withheld"
          % (os.path.relpath(ROSTER, ROOT), as_of, len(circuits), j, " and ".join(years), d,
             len(withheld)))
    for circ, w in sorted(withheld, key=lambda x: (x[0], x[1]["name"])):
        print("  withheld: %s, %s (%s), listed as a %s: %s"
              % (circuit_name(circ), w["name"], w.get("elected") or w.get("sittingFrom"),
                 w["listedAs"], w["listedName"]))
    lines = disagreements(judges, das, directory)
    print("  the court directory and the ballots differ in %d places (changing nothing):"
          % len(lines))
    for line in lines:
        print("    " + line)
    if pending:
        print("  results not yet official, read again next run: %s" % ", ".join(sorted(pending)))


def tilings(record):
    rows = [(name, sorted(rec["counties"]), {}) for name, rec in sorted(record["circuits"].items())]
    return [wcc.Tiling(CIRCUITS_FILE, "judicial circuit", rows, CIRCUITS,
                       "the Secretary of State's official results: each county's newest ballot "
                       "carrying a superior court judge's or district attorney's contest")]


# --------------------------------------------------------------- checking

def check():
    with open(RECORD, encoding="utf-8") as fh:
        record = json.load(fh)
    wcc.check(TAG, LABEL, tilings(record))
    with open(ROSTER, encoding="utf-8") as fh:
        roster = json.load(fh)
    errs = []
    days = {rec.get("asOf") for rec in roster.values()}
    as_of = days.pop() if len(days) == 1 else ""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", as_of or ""):
        errs.append("the circuits were not all read on one day: %s" % sorted(map(str, days | {as_of})))
    if set(roster) != set(record["circuits"]):
        errs.append("the roster's circuits are not the record's")
    for circ, rec in record["circuits"].items():
        for county, ev in rec["counties"].items():
            ok = [c for c in ev["contests"] if parse(c) and
                  circuit_name(RENAMED.get(parse(c)[1], parse(c)[1])) == circ]
            if not ok or len(ok) != len(ev["contests"]):
                errs.append("%s: the record's contests %s do not name %s"
                            % (county, ev["contests"], circ))

    def rule_since(who):
        return who["elected"] if who.get("special") else "%d-01-01" % (int(who["elected"][:4]) + 1)

    def held(who, where, now):
        if not who.get("name") or not who.get("election") or not who.get("electionName"):
            errs.append("%s: %r carries no name or election" % (where, who))
            return
        if who.get("since") != rule_since(who):
            errs.append("%s: %s took office %r, not %r" % (where, who["name"], who.get("since"),
                                                          rule_since(who)))
        elif now and not (who["since"] <= as_of < term_end(who["since"])):
            errs.append("%s: %s was not in office on %s" % (where, who["name"], as_of))
        elif not now and who["since"] <= as_of:
            errs.append("%s: %s is listed as elected, not yet in office, but took office %s"
                        % (where, who["name"], who["since"]))

    for circ, rec in sorted(roster.items()):
        years = rec.get("judgeElections") or []
        people = []
        for s in rec.get("judges") or []:
            where = "%s judge seat %r" % (circ, s.get("seat"))
            if s.get("withheld"):
                w = s["withheld"]
                if s.get("name") or not w.get("listedAs") or not w.get("listedName"):
                    errs.append("%s: a withheld seat names someone or says nothing" % where)
                if s.get("elect"):
                    held(s["elect"], where, False)
                continue
            if s.get("runoff"):
                if s.get("name") or s.get("elect"):
                    errs.append("%s: a seat waiting on its runoff names someone" % where)
                continue
            if s.get("elect"):
                held(s["elect"], where, False)
                if s.get("name") and not s.get("sittingFrom"):
                    errs.append("%s: a sitting judge with no ballot" % where)
            else:
                held(s, where, True)
            for who in (s, s.get("elect") or {}):
                if who.get("elected") and who["elected"][:4] not in years:
                    errs.append("%s: elected %s, outside the judges' elections %s"
                                % (where, who["elected"], years))
            people.append(s.get("name"))
        named = [p for p in people if p]
        if len(named) != len(set(named)):
            errs.append("%s: a judge named twice" % circ)
        da = rec.get("districtAttorney") or {}
        if da.get("name"):
            held(da, "%s district attorney" % circ, True)
            if any(same_person(da["name"], p) for p in named):
                errs.append("%s: the district attorney is also named a judge" % circ)
        if da.get("elect"):
            held(da["elect"], "%s district attorney" % circ, False)
    j = sum(1 for rec in roster.values() for s in rec["judges"] if s.get("name") or s.get("elect"))
    d = sum(1 for rec in roster.values() if rec["districtAttorney"].get("name"))
    if j < MIN_JUDGES or d < MIN_DAS:
        errs.append("%d judges and %d district attorneys named, under the floors of %d and %d"
                    % (j, d, MIN_JUDGES, MIN_DAS))
    if errs:
        fail("%s\n  %s" % (os.path.relpath(ROSTER, ROOT), "\n  ".join(errs[:40])))
    print("%s: OK as of %s, %d circuits, %d judges named or elected, %d district attorneys named"
          % (LABEL, as_of, len(record["circuits"]), j, d))


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--cache", help="keep what is fetched here, and read it back on the next run")
    ap.add_argument("--offline", action="store_true", help="fetch nothing (needs --cache)")
    ap.add_argument("--as-of", help="name who holds each office on this day (default: today)")
    ap.add_argument("--draw", action="store_true", help="also draw the circuits (needs shapely)")
    ap.add_argument("--check", action="store_true", help="check what is written, offline")
    args = ap.parse_args()
    if args.check:
        check()
    else:
        build(args)


if __name__ == "__main__":
    main()
