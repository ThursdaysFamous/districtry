#!/usr/bin/env python3
"""
Name Georgia's county commissioners and county school board members from the
Secretary of State's official election results, and write
ga/data/app/ga-county-officials.json.

This is the names half of step 3 of the Georgia launch plan. No state office
publishes who sits on Georgia's county commissions and school boards: the
county commissioners' association lists each county's office and none of its
members, and the Department of Community Affairs' directory of local
officials sits behind a sign-in, which stays shut. So the names come from the
elections that chose them, and every seat says which election that was.

THE SOURCE, MEASURED 2026-10-30.

  results.sos.ga.gov (robots.txt answers 404: no policy, allow all).
  /results/public/api/jurisdictions/Georgia lists every election the site
  carries, 117 on 2026-10-30, each with an id and a date.
  /results/public/api/elections/Georgia/<election>/data lists the counties
  that voted in it, and /results/public/api/elections/<county>/<election>/data
  lists that county's contests, each candidate's votes and party, and whether
  the county's results are official. The site carries county contests only
  from the general election of 5 November 2024 on: its pages for 2022 and for
  May 2024 hold state, federal and court races. It shows nobody appointed to
  fill a vacancy. sos.ga.gov itself answers robots.txt with a challenge page
  and is not read.

  The contests are the same ones ga/scripts/check_ga_county_maps.py tests the
  county maps with, found by the same reading of their names (`parse` there),
  so the two cannot disagree about which contests are a county board's.

WHO HOLDS A SEAT. A seat is named for the winner of its newest contest whose
winner has taken office on the day this runs, and nobody else:

  - A contest's winner is the candidate with more than half its votes, as
    Georgia's law requires; in a runoff, the candidate with the most. A
    candidate alone on the ballot is elected whatever the count, and a
    contest electing several members from no more candidates elects them all
    (`winners`). A contest nobody won outright waits for its runoff; where
    the site does not carry the runoff, the seat says so (`runoff`) and names
    nobody.
  - A party's primary chooses a nominee, not an officeholder, so it names
    nobody. It does say the seat exists and is on the next general election's
    ballot.
  - A special election fills a vacancy, and its winner is counted from the
    day of the election. Every other contest is a regular election, whose
    winner takes office on 1 January of the next year: the November general
    elections, and the nonpartisan elections in May that choose most school
    boards and the consolidated governments' commissions. The site marks
    most special elections; one it does not mark is read as special when it
    falls where no regular county election does (`unmarked_special`), and the
    card does not call it one.
  - A winner is named for at most one four-year term from the day they took
    office (TERM_YEARS).
  - Results the site does not yet mark official are not read at all; the
    county's contests in that election wait for the next run.

  So a seat is listed only when a contest for it is on the site, which means
  on a ballot from November 2024 on. A seat last filled before then and not
  on a ballot since is not listed, which is most of the seats chosen in the
  nonpartisan election of May 2024. A seat on a ballot since then whose
  winner was chosen earlier (one only in a 2026 primary so far, say) is
  listed with no name. A seat whose winner has not taken office yet carries
  that winner as `elect`, with the month they take office. A vacancy filled
  by appointment is invisible here, which every card says in the words
  "Where the names come from".

A CITY'S BOARD is left out: where a city votes with its county, the county's
results carry the city's school board and council too, and `city_board` sets
them aside by their names. Every run prints the contests it set aside.

A SEAT is what a contest's name says after the county board's own words are
taken out: "County Commission - District 2" is District 2, "BOE - Post 4" is
Post 4, "County Commission Chairman" is the chair. Two contests name the same
seat when those words match once spelling is evened out (`seat_key`). The
handful of contest names that read some other way are recorded in
SEAT_NAMES, with what each one says and why, and a contest naming a seat in
words this builder has not seen stops the build.

Usage:
  python3 ga/scripts/build_ga_county_officials.py [--cache DIR] [--as-of DATE]
  python3 ga/scripts/build_ga_county_officials.py --check   # offline, stdlib only
"""

import argparse
import datetime
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE_ROOT = os.path.dirname(_HERE)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import check_ga_county_maps as cmap  # noqa: E402  (same instance: the contest reading)

DEFAULT_OUT = os.path.join(INSTANCE_ROOT, "data", "app", "ga-county-officials.json")
COUNTIES = os.path.join(INSTANCE_ROOT, "data", "app", "state-counties.json")
JURISDICTION = "https://results.sos.ga.gov/results/public/api/jurisdictions/Georgia"
RESULTS_PAGE = "https://results.sos.ga.gov/results/public/Georgia"
# The first election whose county contests the site carries.
FIRST_ELECTION = "2024-11-05"

# Contests `cmap.parse` reads as a county board's that are not one: the
# Public Service Commission and the insurance commissioner, whose names carry
# "commission(er)", and the questions put to a school board's voters, which
# the site files as candidate contests (measured 2026-10-30: Columbia's
# homestead exemption, Taylor's bonds, Lincoln's resolution).
NOT_A_BOARD = re.compile(
    r"\bPSC\b|public service|insurance|reconstitution|homestead|exemption|"
    r"\bbonds?\b|resolution|referendum|question|\btax\b|\be?splost\b", re.I)

# A CITY'S BOARD ON THE COUNTY'S BALLOT. Where a city votes with its county,
# the county's results carry the city's school board and commission too
# (measured 2026-10-30: Atlanta's, Decatur's, Marietta's, Cartersville's and
# 14 more city boards, almost all on the municipal ballot of 4 November
# 2025). A county board's contest names no place but its county: it leads
# with "County", the county's name, a special-election marker or the board's
# own words, and it ends with the seat. So a contest that leads with any
# other word ("Cartersville School Board", "Atlanta Board of Education",
# "City of Valdosta - School Board") or, without the word County, ends with
# one ("Board of Education - Rome", "BOE Chairman - Social Circle") is a
# city's, and so is one naming a ward, a city or a municipality. `city_board`
# says which, and every run prints the contests it set aside.
BOARD_START = re.compile(
    r"\bBOE\b|\bBd\b|\bboard\b|\bschool\b|\bcommis|\bcom+is+i?on|\bcomission|"
    r"\bcouncil\b|\bmember\b|\bchair|\bsole\b", re.I)
LEAD_WORDS = re.compile(
    r"\((?:s|se)\)|\bspecial(?:\s+election)?\b|\bnonpartisan\b|\bcounty\b|\bco\b", re.I)
SEAT_WORDS = re.compile(
    r"\bdist(?:rict)?\b|\bpost\b|\bseat\b|\bzone\b|\bsuper\b|\bat\s*large\b|\blrg\b|"
    r"\bchair|\bvice\b|\bpresident\b|\bsole\b|\bmember\b|\brepresentative\b|"
    r"\bBOE\b|\bboard\b|\beducation\b|\bcom+is+i?on|\bcomission|\bcouncil\b|"
    r"\d|^[A-Z]$|\(", re.I)
# A consolidated government's contest leads with the city's name, which is
# the county's government too (Richmond's "Augusta Commission").
CONSOLIDATED = {"richmond": "Augusta", "clarke": "Athens", "muscogee": "Columbus",
                "bibb": "Macon"}

# The party a contest name ends with: a primary chooses a nominee, not an
# officeholder. Counties write it " - Rep", " (Dem)", "- Rep" and, once,
# with two spaces and no hyphen (Fulton's "District 5  Dem"), so the
# separator is any run of spaces, hyphens and an opening bracket.
PARTY_TAIL = re.compile(r"[\s\-(]+(?:Rep|Dem|Republican|Democrat|Democratic)\)?\s*$", re.I)
# The same, with the marks a nonpartisan contest carries, taken out of a seat.
PARTY_ANY = re.compile(
    r"[\s\-(]+(?:Rep|Dem|Republican|Democrat|Democratic|NP|Nonpartisan)\)?\s*$", re.I)

# Words a contest name uses for the board itself, taken out to leave the seat.
BOARD_WORDS = re.compile(
    r"\b(?:member,?|county|board\s+of\s+commission(?:er)?s?|board\s+of\s+commission|"
    r"commis+i?on(?:er)?s?|com+is+i?on(?:er)?s?|commisson|comission|"
    r"board\s+of\s+education|board\s+of\s+ed|bd\s+of\s+ed|boe|school\s+board|"
    r"representative|nonpartisan|augusta|athens|columbus|macon|council|board|of)\b", re.I)
SPECIAL = re.compile(r"\bspecial\b|\(s\)|\(se\)|\bse\)", re.I)
CHAIR = re.compile(r"\bchair(?:man|person|woman)?(?:/person)?\b", re.I)

# The words a seat may be named with once `seat_key` has evened out its
# spelling. A contest whose seat reads any other way stops the build: it is
# a board this builder has not seen named that way, and a person reads it
# and records it in SEAT_NAMES (or teaches `city_board` a new city).
SEAT_TOKEN = re.compile(
    r"district|post|seat|zone|super|at-large|chair|vice|president|sole|\d+[a-z]?|[a-z]")

# Contest names `seat_label` cannot read, each with the seat it names and
# the reason, keyed by (county key, the contest's name as the site prints it).
# Measured 2026-10-30 against every county board contest on the site.
SEAT_NAMES = {
    # Baker County's commission and school board are elected from five
    # districts named for places, not numbered.
    ("baker", "County Commission - Anna"): "Anna",
    ("baker", "County Commission - Elmodel"): "Elmodel",
    ("baker", "County Commission - Hogards Mill"): "Hogards Mill",
    ("baker", "County Commission - Milford"): "Milford",
    ("baker", "County Commission - Newton"): "Newton",
    ("baker", "County BOE - Anna"): "Anna",
    ("baker", "County BOE - Elmodel"): "Elmodel",
    ("baker", "County BOE - Hogards Mill"): "Hogards Mill",
    ("baker", "County BOE - Milford"): "Milford",
    ("baker", "County BOE - Newton"): "Newton",
    # Fannin County's results name each school board seat for the member
    # who held it when it went on the ballot, and nothing else; the card
    # prints that name as the seat's, as the ballot did.
    ("fannin", "County BOE (Bramlett)"): "Bramlett seat",
    ("fannin", "County BOE (Deweese)"): "Deweese seat",
    ("fannin", "County BOE (Galloway)"): "Galloway seat",
    ("fannin", "County BOE - Bearden - Rep"): "Bearden seat",
    ("fannin", "County BOE - Cole - Rep"): "Cole seat",
    # Glascock's two numbered districts carry the town each is named for.
    ("glascock", "County Commission - District 1 Gibson"): "District 1",
    ("glascock", "County Commission - District 3 Mitchell"): "District 3",
    # Towns's school board posts carry the town each member lives in.
    ("towns", "County BOE - Post 2 - Young Harris"): "Post 2",
    ("towns", "County BOE - Post 3 - Hiawassee"): "Post 3",
    # Chattooga is governed by a sole commissioner (measured for the Georgia
    # plan, 2026-10-21: the county has no commission map), and this, its
    # only commission contest on the site, elects that commissioner; the
    # ballot calls the seat at large.
    ("chattooga", "County Commissioner - At Large"): "Sole commissioner",
    # Liberty's contest with no seat named, on the 2024 ballot beside its
    # districts' own: it drew 22,549 votes against 3,103 to 3,412 in each of
    # the three district contests there, so it is the seat elected
    # county-wide. The county's map has six districts.
    ("liberty", "Board of Commissioners"): "At large",
}

PARTIES = {"rep": "Republican", "dem": "Democratic", "ind": "Independent",
           "lib": "Libertarian", "grn": "Green"}


def city_board(name, county):
    """True when a county's contest is a city's board (see above)."""
    if re.search(r"\bward\b|\bcity\b|\bmunicipal\b", name, re.I):
        return True
    core = PARTY_ANY.sub("", name).strip()
    m = BOARD_START.search(core)
    lead = core[:m.start()] if m else core
    lead = re.sub(r"\b%s\b" % re.escape(county), " ", lead, flags=re.I)
    city = CONSOLIDATED.get(cmap.county_key(county))
    if city:
        lead = re.sub(r"\b%s\b" % city, " ", lead, flags=re.I)
    if re.search(r"[A-Za-z]", LEAD_WORDS.sub(" ", lead)):
        return True
    if not re.search(r"\bcounty\b", core, re.I):
        # a sitting member's name in brackets is not a place, and can carry
        # a hyphen of its own (Chatham's "District 8 (Howard-Hall)")
        tail = re.split(r"\s*-\s*", re.sub(r"\s*\([^)]*\)\s*$", "", core))[-1].strip()
        if tail and not SEAT_WORDS.search(tail):
            return True
    return False


def seat_key(label):
    """Two seat labels name one seat when this agrees. A seat named by a
    number alone ("County Commission 1") is that district: it is how the map
    check in check_ga_county_maps.py read every such contest, and every map it
    passed agreed. A number and a letter alone ("Commissioner- 1-B") is that
    district's seat, as the same county writes it elsewhere ("Dist 1 - Seat
    A")."""
    s = label.lower()
    s = CHAIR.sub("chair", s)
    s = re.sub(r"\bdist\.?\b|\bd(?=\d)", "district ", s)
    s = re.sub(r"\bat[- ]large\b|\blrg\b", "at-large", s)
    s = re.sub(r"[^a-z0-9-]+", " ", s)
    s = re.sub(r"(?<![a-z])-|-(?![a-z])", " ", s)
    s = re.sub(r"\b0+(\d)", r"\1", s)
    s = " ".join(s.split())
    s = re.sub(r"^(\d+[a-z]?)\b", r"district \1", s)
    s = re.sub(r"^(district \d+) ([a-z])$", r"\1 seat \2", s)
    return s


def seat_label(name, county):
    """The seat a contest's name names, in its own words, or ''. `county` is
    the county's own name, which some contest names lead with. A name in
    brackets after a numbered seat is the member who held it when it went on
    the ballot (Chatham's "BOE - District 4 (Kachmar)"), and is left out."""
    s = PARTY_ANY.sub("", name)
    s = s.split("/")[0]
    s = re.sub(r"\b%s\b" % re.escape(county), " ", s, flags=re.I)
    s = re.sub(r"\((?:special(?: primary)?|s|se|sp)\)|\bspecial(?: election)?\b|-\s*special\b",
               " ", s, flags=re.I)
    s = re.sub(r"(\d[A-Za-z]?)\s*\([A-Z][A-Za-z'. -]+\)\s*$", r"\1", s)
    s = BOARD_WORDS.sub(" ", s)
    s = re.sub(r"^[\s,:-]+|[\s,:-]+$", "", s)
    s = re.sub(r"\s*-\s*", " - ", s)
    s = re.sub(r"\s+", " ", s).strip(" -,")
    return s


def clean_name(text):
    """A candidate as the site prints them, less the incumbent mark and party."""
    s = re.sub(r"\((?:I|Rep|Dem|Ind|Lib|NP|Grn|Inc)\)", " ", text)
    return re.sub(r"\s+", " ", s).strip(" ,")


def winners(item, runoff):
    """([(name, party, votes)], total votes) of a contest's winners, or
    (None, total) when nobody won outright, or (("contested", n), total) for
    a contest electing n members from more than n candidates.

    One candidate on the ballot is elected, whatever the count: McDuffie's
    unopposed school board member shows 0 votes on an official result. A
    contest electing several members from no more candidates elects them all
    (Calhoun's two at-large school board seats, 2024). More candidates than
    seats needs Georgia's rule for counting a majority among several seats,
    which this builder does not apply; no such county board contest was on
    the site on 2026-10-30, and one stops the build."""
    opts = []
    for o in item["summaryResults"]["ballotOptions"]:
        party = ((o.get("party") or {}).get("abbreviation") or "").strip().lower()
        opts.append((cmap.text(o["name"]), PARTIES.get(party), o.get("voteCount") or 0,
                     bool(o.get("isWriteIn"))))
    total = sum(o[2] for o in opts)
    m = re.search(r"(\d+)", cmap.text(item.get("voteFor")) or "1")
    n = int(m.group(1)) if m else 1
    listed = [o for o in opts if not o[3]]
    if listed and len(listed) <= n and all(o[2] >= w[2] for o in listed
                                           for w in opts if w[3]):
        return [(clean_name(o[0]), o[1], o[2]) for o in listed], total
    if n != 1:
        return ("contested", n), total
    ranked = sorted(opts, key=lambda o: -o[2])
    if not ranked or not total:
        return None, total
    top = ranked[0]
    if len(ranked) > 1 and ranked[1][2] == top[2]:
        return None, total
    if not runoff and top[2] * 2 <= total:
        return None, total
    if top[3]:
        return None, total
    return [(clean_name(top[0]), top[1], top[2])], total


# --------------------------------------------------------------- reading

def elections(cache):
    """[(id, date, name)] of every election the site carries from
    FIRST_ELECTION on, oldest first. Recounts re-report an earlier election's
    contest and are skipped; none of them, measured 2026-10-30, is a county
    board's."""
    page = json.loads(fresh(cache, ("elections.json",), JURISDICTION) or "null")
    if not page:
        raise SystemExit("FAIL: %s answered nothing" % JURISDICTION)
    out = []
    for e in page.get("elections") or []:
        day = e.get("electionDate") or ""
        name = cmap.text(e.get("name"))
        if day < FIRST_ELECTION or re.search(r"\brecount\b", name, re.I):
            continue
        out.append((e["publicElectionId"], day, name.strip()))
    if not any(el == "2024NovGen" for el, _, _ in out):
        raise SystemExit("FAIL: the site's list of elections no longer names 2024NovGen")
    return sorted(out, key=lambda x: (x[1], x[0]))


def fresh(cache, parts, url):
    """`url`'s body, fetched every run and kept under `cache` for an
    --offline run to read back."""
    path = os.path.join(cache, "results", *parts) if cache else None
    if cmap.OFFLINE:
        if not path or not os.path.exists(path):
            raise SystemExit("FAIL: --offline and the cache holds no copy of %s" % url)
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    body = cmap.fetch(url, accept="application/json")
    if path:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path + ".part", "w", encoding="utf-8") as fh:
            fh.write(body or "")
        os.replace(path + ".part", path)
    return body


def official(d):
    return bool(((d or {}).get("election") or {}).get("isOfficialResults"))


def read_county(cache, el, sn):
    """A county's results in one election. A kept copy is read back only once
    the site marks it official, since official results do not change; any
    other is fetched again."""
    url = cmap.RESULTS_API + "%s/%s/data" % (sn, el)
    path = os.path.join(cache, "results", el, sn, "data.json") if cache else None
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        d = json.loads(text) if text else None
        if official(d) or cmap.OFFLINE:
            return d
    body = fresh(cache, (el, sn, "data.json"), url)
    return json.loads(body) if body else None


def read_state(cache, el):
    """The counties that voted in an election, read every run."""
    body = fresh(cache, (el, "Georgia.json"), cmap.RESULTS_API + "Georgia/%s/data" % el)
    return json.loads(body) if body else None


def read_contests(cache, els):
    """Every county board contest in `els`, and the elections whose county
    results are not official yet: ([contest], [(election, county)])."""
    contests, pending = [], []
    for el, day, label in els:
        state = read_state(cache, el)
        counties = ((state or {}).get("jurisdiction") or {}).get("childLocalities") or []
        runoff_election = bool(re.search(r"runoff", label, re.I))
        special_election = bool(re.search(r"special", label, re.I)) and not re.search(
            r"general|primary", label, re.I)
        for c in counties:
            sn = c["shortName"]
            ckey = cmap.county_key(sn.replace("-county-ga", "").replace("-", " "))
            d = read_county(cache, el, sn)
            if not d:
                raise SystemExit("FAIL: no %s results for %s" % (el, sn))
            items = [bi for bi in d.get("ballotItems") or [] if bi.get("contestType") == "Candidate"]
            boards = []
            for bi in items:
                name = cmap.text(bi["name"])
                pr = cmap.parse(name, ckey)
                if not pr or NOT_A_BOARD.search(name):
                    continue
                boards.append((bi, name, pr))
            if not boards:
                continue
            if not official(d):
                pending.append((el, ckey))
                continue
            for bi, name, pr in boards:
                primary = bool(PARTY_TAIL.search(name))
                runoff = runoff_election or bool(re.search(r"runoff", name, re.I))
                won, total = (None, 0) if primary else winners(bi, runoff)
                contests.append({
                    "election": el, "date": day, "electionName": label, "county": ckey,
                    "contest": name, "body": pr["body"],
                    "primary": primary, "runoff": runoff,
                    "special": special_election or bool(SPECIAL.search(name)),
                    "won": won, "votes": total,
                })
        print("  read %s (%s)" % (el, day), file=sys.stderr, flush=True)
    return contests, pending


# --------------------------------------------------------------- the roster

# A regular term on these boards is four years. A winner is named for at most
# that long from the day they took office, so a seat whose next election this
# builder has not read reads as not listed rather than naming someone whose
# term has ended.
TERM_YEARS = 4


def took_office(c):
    """The day a contest's winner takes office: a special election's on its
    own day, every other on 1 January of the next year."""
    if c["special"]:
        return c["date"]
    return "%d-01-01" % (int(c["date"][:4]) + 1)


def term_end(since):
    y, rest = int(since[:4]), since[4:]
    return "%d%s" % (y + TERM_YEARS, rest)


def season(date):
    """When in the year a contest fell: "may" for the nonpartisan general
    election held with the primary in May and its June runoff, "nov" for the
    general election and its December runoff, else None. Georgia holds its
    regular county elections in even years and in those two seasons only."""
    return {"05": "may", "06": "may", "11": "nov", "12": "nov"}.get(date[5:7])


def board_seasons(contests):
    """{(county, body): season} -- the season in which each county's board is
    regularly elected: the one holding most of its won contests the site does
    not call special, in even years. A board elected as often in both seasons
    has none."""
    tally = {}
    for c in contests:
        if (c["primary"] or not c["won"] or c["special"]
                or int(c["date"][:4]) % 2 or not season(c["date"])):
            continue
        t = tally.setdefault((c["county"], c["body"]), {"may": 0, "nov": 0})
        t[season(c["date"])] += 1
    return {k: ("may" if t["may"] > t["nov"] else "nov" if t["nov"] > t["may"] else None)
            for k, t in tally.items()}


def unmarked_special(c, seasons):
    """True when a contest the site does not call special must be one,
    because it falls where no regular county election does: in an odd year,
    in a month other than May, June, November or December, or in the other
    season from its board's regular one. Measured 2026-10-30 against the
    935 won county board contests (27 of them marked special by the site),
    this marks 16: Chatham's "County Commissioner - District 4 (Farrell)" on
    the May 2026 ballot (the commission's other nine seats were all elected
    in November 2024, Pat Farrell's among them), Emanuel's and Seminole's
    two school board seats each on the November 2024 ballot (both boards'
    other contests are in May), and 11 county contests on the municipal
    ballot of November 2025.

    The roster records such a contest as "special": "inferred", and its
    winner as in office from election day, and the card does not call it a
    special election: a county whose board is elected in odd years by its own
    act would read as one here. Measured 2026-10-30, only the May 2026
    contest in Chatham changes who is named: every other one's winner would
    otherwise have taken office on a 1 January already past, so the same
    person is named either way."""
    if int(c["date"][:4]) % 2 or not season(c["date"]):
        return True
    usual = seasons.get((c["county"], c["body"]))
    return bool(usual) and season(c["date"]) != usual


# How a reader sees a seat's words: each word that starts a part of the seat's
# name, and the order the parts are joined in ("District 2, Post 1").
HEADS = {"district": "District", "post": "Post", "seat": "Seat", "zone": "Zone",
         "super": "Super district", "at-large": "at large", "chair": "Chair",
         "vice": "Vice chair", "president": "President", "sole": "Sole commissioner"}


def display(key):
    """A seat's label for a reader, from its key."""
    parts = []
    toks = key.split()
    i = 0
    while i < len(toks):
        t = toks[i]
        if t == "super" and i + 1 < len(toks) and toks[i + 1] == "district":
            i += 1
        if t == "vice" and i + 1 < len(toks) and toks[i + 1] == "chair":
            i += 1
        if t in HEADS:
            parts.append(HEADS[t])
        elif parts:
            parts[-1] += " " + t.upper()
        else:
            parts.append(t.upper())
        i += 1
    out = ", ".join(parts)
    return out[:1].upper() + out[1:]


def seat_district(key):
    """The district number a seat is elected from, or None: "district 4",
    "district 4 at-large" (a district whose member the whole county elects)
    and a district's own posts or seats ("district 2 post 1")."""
    m = re.fullmatch(r"district (\d+)(?: at-large| post \d+| seat [a-z])?", key)
    return int(m.group(1)) if m else None


def build(contests, pending, as_of, names):
    """The roster, {fips: {"county", "commission": [seat], "schoolBoard":
    [seat]}}, and the contests set aside as a city's board."""
    by_key = {cmap.county_key(n): (fips, n) for fips, n in names.items()}
    seats, problems, cities = {}, [], []
    seasons = board_seasons([c for c in contests
                             if not city_board(c["contest"], by_key.get(c["county"], ("", ""))[1])])
    for c in contests:
        if c["county"] not in by_key:
            raise SystemExit("FAIL: results county %r is not one of the 159" % c["county"])
        fips, cname = by_key[c["county"]]
        fixed = SEAT_NAMES.get((c["county"], c["contest"]))
        if not fixed and city_board(c["contest"], cname):
            cities.append("%s %s: %s" % (c["election"], cname, c["contest"]))
            continue
        label = fixed or seat_label(c["contest"], cname)
        key = seat_key(label)
        if not key:
            problems.append("%s %s: %r names no seat" % (c["election"], cname, c["contest"]))
            continue
        if not fixed and not all(SEAT_TOKEN.fullmatch(t) for t in key.split()):
            problems.append("%s %s: %r reads as the seat %r, a name this builder does not "
                            "know" % (c["election"], cname, c["contest"], key))
            continue
        s = seats.setdefault((fips, c["body"], key),
                             {"key": key, "label": fixed or display(key), "won": [], "open": []})
        if c["primary"]:
            continue
        if isinstance(c["won"], tuple):
            problems.append("%s %s: %r elects %d members from more candidates"
                            % (c["election"], cname, c["contest"], c["won"][1]))
            continue
        if not c["won"]:
            if c["votes"]:
                s["open"].append(c["date"])
            continue
        # true when the site calls the contest special; "inferred" when it
        # must be one by `unmarked_special`, which the card does not claim
        special = True if c["special"] else ("inferred" if unmarked_special(c, seasons)
                                             else None)
        since = c["date"] if special else took_office(c)
        s["won"].append({"names": [(n, p) for n, p, _ in c["won"]],
                         "election": c["election"], "elected": c["date"],
                         "since": since, "special": special or None})
    if problems:
        raise SystemExit("FAIL: %d contests this builder cannot read:\n  %s"
                         % (len(problems), "\n  ".join(problems)))
    out = {fips: {"county": names[fips], "commission": [], "schoolBoard": []}
           for fips in sorted(names)}
    for (fips, body, key), s in seats.items():
        won = sorted(s["won"], key=lambda w: (w["since"], w["elected"]))
        now = [w for w in won if w["since"] <= as_of < term_end(w["since"])]
        later = [w for w in won if w["since"] > as_of]
        seat = {"seat": s["label"]}
        d = seat_district(key)
        if d is not None:
            seat["district"] = d
        seat.update(holder(now[-1] if now else None))
        if not now and s["open"] and (not won or max(s["open"]) > won[-1]["elected"]):
            seat["runoff"] = max(s["open"])
        if later:
            seat["elect"] = holder(later[-1])
        out[fips]["commission" if body == "commission" else "schoolBoard"].append(seat)
    for rec in out.values():
        for body in ("commission", "schoolBoard"):
            rec[body].sort(key=seat_order)
    return out, cities


def holder(w):
    """A winner as a seat records them: one member's name and party, or the
    members a contest electing several chose."""
    if not w:
        return {"name": None}
    rec = {}
    if len(w["names"]) == 1:
        rec["name"], party = w["names"][0]
        if party:
            rec["party"] = party
    else:
        rec["name"] = None
        rec["members"] = [dict([("name", n)] + ([("party", p)] if p else []))
                          for n, p in w["names"]]
    for k in ("elected", "election", "special", "since"):
        if w.get(k) is not None:
            rec[k] = w[k]
    return rec


def seat_order(seat):
    key = seat_key(seat["seat"])
    if key.startswith(("chair", "sole", "president", "vice")):
        rank = 0
    elif seat.get("district") is not None:
        rank = 1
    elif key.startswith(("district", "super")):
        rank = 2
    elif key.startswith("post"):
        rank = 3
    else:
        rank = 4
    nums = [int(n) for n in re.findall(r"\d+", key)]
    return (rank, nums, key)


# --------------------------------------------------------------- output

# Floors: a run naming fewer has read the site wrong, not found the boards
# smaller. Measured 2026-10-30, 443 county commissioners and 235 school board
# members were named that day, and 461 and 459 are named once the winners of
# 2026's elections take office on 1 January 2027.
MIN_NAMED = {"commission": 400, "schoolBoard": 200}


def county_names():
    with open(COUNTIES, encoding="utf-8") as fh:
        fc = json.load(fh)
    return {f["properties"]["GEOID"]: f["properties"]["BASENAME"] for f in fc["features"]}


def seated(seat):
    """How many people a seat's record names now."""
    return len(seat.get("members") or []) or (1 if seat.get("name") else 0)


def write(roster, cities, els, pending, as_of, out):
    """One record per county, keyed by FIPS code like the fleet's other county
    rosters: {county, asOf, commission: [seat], schoolBoard: [seat],
    pending?: [election]}. Each named seat carries its election's id, name and
    date. `cities` are the contests set aside as a city's board, printed so a
    run's log shows every one."""
    names = {el: label for el, _, label in els}
    waiting = {}
    for el, ckey in pending:
        waiting.setdefault(ckey, set()).add(el)
    doc = {}
    for fips, rec in roster.items():
        for body in ("commission", "schoolBoard"):
            for s in rec[body]:
                for who in (s, s.get("elect")):
                    if who and who.get("election"):
                        who["electionName"] = names[who["election"]]
        out_rec = {"county": rec["county"], "asOf": as_of,
                   "commission": rec["commission"], "schoolBoard": rec["schoolBoard"]}
        late = sorted(waiting.get(cmap.county_key(rec["county"]), ()))
        if late:
            out_rec["pending"] = late
        doc[fips] = out_rec
    named = {b: sum(seated(s) for r in roster.values() for s in r[b])
             for b in ("commission", "schoolBoard")}
    for b, floor in MIN_NAMED.items():
        if named[b] < floor:
            raise SystemExit("FAIL: %d %s seats named, under the floor of %d" % (named[b], b, floor))
    tmp = out + ".part"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    os.replace(tmp, out)
    seats = {b: sum(len(r[b]) for r in roster.values()) for b in ("commission", "schoolBoard")}
    elect = {b: sum(1 for r in roster.values() for s in r[b] if "elect" in s)
             for b in ("commission", "schoolBoard")}
    print("wrote %s as of %s: commission %d people named in %d seats listed (%d seats with "
          "a winner not yet in office); school board %d in %d (%d)"
          % (out, as_of, named["commission"], seats["commission"], elect["commission"],
             named["schoolBoard"], seats["schoolBoard"], elect["schoolBoard"]))
    print("  %d contests set aside as a city's board:" % len(cities))
    for line in sorted(cities):
        print("    " + line)
    if pending:
        print("  results not yet official, read again next run: %s"
              % ", ".join(sorted("%s %s" % p for p in pending)))


def check(path):
    """Offline: the shipped roster's shape, and that every name it gives
    follows from the rules above as of the day it was written."""
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    names = county_names()
    errs = []
    if set(doc) != set(names):
        errs.append("counties differ from state-counties.json: %s" % sorted(set(doc) ^ set(names)))
    named = {"commission": 0, "schoolBoard": 0}
    dates = set()
    for fips, rec in sorted(doc.items()):
        if rec.get("county") != names.get(fips):
            errs.append("%s: county %r is not %r" % (fips, rec.get("county"), names.get(fips)))
        as_of = rec.get("asOf") or ""
        dates.add(as_of)
        for body in ("commission", "schoolBoard"):
            keys = set()
            for s in rec.get(body) or []:
                where = "%s %s %s" % (fips, body, s.get("seat"))
                key = seat_key(s.get("seat") or "")
                if not key or key in keys:
                    errs.append("%s: seat empty or listed twice" % where)
                keys.add(key)
                if seat_district(key) != s.get("district"):
                    errs.append("%s: district %r does not follow from the seat"
                                % (where, s.get("district")))
                if s.get("name") and s.get("members"):
                    errs.append("%s: names one member and several" % where)
                if (s.get("runoff") and (s.get("name") or s.get("members")
                                         or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", s["runoff"]))):
                    errs.append("%s: a runoff date on a seat that names someone" % where)
                for who, rule in ((s, "now"), (s.get("elect"), "later")):
                    if not who or not (who.get("name") or who.get("members")):
                        continue
                    people = [m.get("name") for m in who.get("members") or []] or [who["name"]]
                    if not all(people) or len(people) != len(set(people)):
                        errs.append("%s: a member with no name, or named twice" % where)
                    if not (who.get("election") and who.get("electionName")
                            and re.fullmatch(r"\d{4}-\d{2}-\d{2}", who.get("elected") or "")):
                        errs.append("%s: %s carries no election" % (where, people))
                        continue
                    if who.get("special") not in (None, True, "inferred"):
                        errs.append("%s: special is %r" % (where, who.get("special")))
                    since = who.get("since") or ""
                    rule_since = (who["elected"] if who.get("special") else
                                  "%d-01-01" % (int(who["elected"][:4]) + 1))
                    if since != rule_since:
                        errs.append("%s: %s took office %r, not %r"
                                    % (where, people, since, rule_since))
                    elif rule == "now" and not (since <= as_of < term_end(since)):
                        errs.append("%s: %s was not in office on %s" % (where, people, as_of))
                    elif rule == "later" and since <= as_of:
                        errs.append("%s: %s is listed as elected, not yet in office, but took "
                                    "office %s" % (where, people, since))
                named[body] += seated(s)
    if len(dates) != 1:
        errs.append("the counties were written as of different days: %s" % sorted(dates))
    for b, floor in MIN_NAMED.items():
        if named[b] < floor:
            errs.append("%d %s members named, under the floor of %d" % (named[b], b, floor))
    if errs:
        raise SystemExit("FAIL: %s\n  %s" % (path, "\n  ".join(errs[:40])))
    print("OK %s: as of %s, %d county commissioners and %d school board members named"
          % (os.path.relpath(path), min(dates), named["commission"], named["schoolBoard"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--cache", help="keep what is fetched here, and read it back on the next run")
    ap.add_argument("--offline", action="store_true", help="fetch nothing (needs --cache)")
    ap.add_argument("--as-of", help="name who holds each seat on this day (default: today)")
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--check", nargs="?", const=DEFAULT_OUT, metavar="PATH",
                    help="check a written roster, offline")
    args = ap.parse_args()
    if args.check:
        check(args.check)
        return
    cmap.OFFLINE = args.offline
    cache = os.path.abspath(args.cache) if args.cache else None
    as_of = args.as_of or datetime.date.today().isoformat()
    els = elections(cache)
    contests, pending = read_contests(cache, els)
    roster, cities = build(contests, pending, as_of, county_names())
    write(roster, cities, els, pending, as_of, args.out)


if __name__ == "__main__":
    main()
