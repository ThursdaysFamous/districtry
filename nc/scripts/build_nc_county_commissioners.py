#!/usr/bin/env python3
"""North Carolina's county commissioners, from the State Board of Elections'
own precinct-level results, every name dated to the election that seated it.

WHAT THIS PUBLISHES AND WHAT IT DOES NOT. Every North Carolina county is run
by an elected board of commissioners. The State Board of Elections publishes
the full results of every general election as one tab-separated file
(`results_pct_<date>.zip` on dl.ncsbe.gov, an S3 bucket whose robots.txt
answers 404, which RFC 9309 files as no policy), and it publishes a candidate
filing list for each election year (`Candidate_Listing_<year>.csv`) that gives
every contest's TERM LENGTH and whether it is an UNEXPIRED term. Between the
two most recent generals whose winners have taken office, those files name a
winner for almost every seat on all 100 boards.

A winner is a fact with a date on it. It is NOT a statement of who holds the
seat today: a North Carolina board fills a vacancy by appointment
(NCGS 153A-27), which no election result records, so a commissioner who has
resigned or died since still shows here as the person who won. So every seat
names its election, and the card and the county page say so in words — the
posture Indiana (in/scripts/build_in_county_officials.py) and Minnesota
(mn/scripts/build_mn_commissioner_roster.py) ship under.

HOW A SEAT IS DECIDED TO BE CURRENT. Terms are two or four years, set county
by county, and the filing list says which. A winner elected at general Y to a
term of T years is still in office if Y + T is later than the newest general
read (2022 + 4 = 2026 is; 2022 + 2 = 2024 is not). Three things change that,
each measured on the 2022 and 2024 files (2026-10-11):
  (1) AN UNEXPIRED-TERM CONTEST replaces somebody. In a single-seat contest it
      is plain who; in a seat group elected several at a time (Union, Wilkes,
      Transylvania in 2024) the results do not say which of the earlier
      winners left, so every one of them carries a note saying so rather than
      this file guessing.
  (2) THE SAME PERSON WINNING AGAIN in the same county keeps only the newer
      win. In Polk the third-placed 2022 winner's seat was on the 2024 ballot,
      which the filing list does not say; the re-election shows it.
  (3) THE NEXT ELECTION'S FILING LIST IS A WITNESS. Every seat whose term ends
      at the next general must appear on that general's filing list, and every
      seat on it must be one this file names. A seat on it as an UNEXPIRED
      term tells us its 2024 winner has since left; that seat names nobody and
      says why. A disagreement this file cannot explain fails the build unless
      `WITNESS_EXCEPTIONS` records it with its reason, and an entry that stops
      disagreeing fails too, so the table cannot rot.

THE SEAT LABEL IS THE CONTEST'S OWN WORDING. "District 3", "At large", "Swan
Quarter Township". A district-named seat may be elected by the whole county
(NCGS 153A-58), and nothing in a result says which, so this file never calls a
board "by district" or "at large" (nc/WATCH.md's standing warning). A contest
named only "<County> County Board of Commissioners" is labelled "Board seat".

A RESULT COUNTS FROM THE DAY ITS WINNERS TAKE OFFICE, the first Monday in
December after the election (NCGS 153A-26). The November 2026 winners reach
this file on the first run after 7 December 2026, once the State Board's
results file for that date exists; until then the people they will replace
are the ones holding those seats.

Usage:
    python3 nc/scripts/build_nc_county_commissioners.py          # fetch and write
    python3 nc/scripts/build_nc_county_commissioners.py --check  # offline gate
"""

import argparse
import collections
import csv
import datetime
import io
import json
import os
import re
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
FLEET_SCRIPTS = os.path.join(os.path.dirname(INSTANCE), "scripts")
sys.path.insert(0, FLEET_SCRIPTS)

from scraper_common import (  # noqa: E402
    UA_HEADERS_ROSTER_BOT, UA_ROSTER_BOT, require_robots_once)

HOST = "https://dl.ncsbe.gov"
RESULTS_ZIP = HOST + "/ENRS/%s/results_pct_%s.zip"
CANDIDATES = HOST + "/Elections/%d/Candidate%%20Filing/Candidate_Listing_%d.csv"
# The State Board's own results page for an election day, which a reader can open.
RESULTS_PAGE = "https://er.ncsbe.gov/?election_dt=%s&county_id=0&office=ALL&contest=0"
REQUEST_TIMEOUT = 120

FIRST_YEAR = 2022
COUNTIES_FILE = os.path.join(INSTANCE, "data", "app", "state-counties.json")
OUT_FILE = os.path.join(INSTANCE, "data", "app", "nc-county-commissioners.json")

# 100 counties, every one with a board. NCACC's election-methods table counts
# 587 commissioners (relayed in nc/WATCH.md, not re-read here: ncacc.org now
# answers a Cloudflare challenge). The floor is a little under that, because
# a seat whose holder has left names nobody.
EXPECT_COUNTIES = 100
MIN_NAMED = 560

PARTY_NAMES = {"DEM": "Democratic", "REP": "Republican", "UNA": "Unaffiliated",
               "LIB": "Libertarian", "GRE": "Green", "CST": "Constitution",
               "JFA": "Justice for All", "NLB": "No Labels"}

CONTEST_RE = re.compile(
    r"^(?P<county>[A-Z .']+?) COUNTY (?:BOARD OF|BD OF)?\s*COMMISSIONERS(?P<rest>.*)$")

# Contests the filing list does not carry, with the term the seat has and the
# evidence for it. Measured 2026-10-11.
DECLARED_TERMS = {
    (2022, "HYDE", "HYDE COUNTY BOARD OF COMMISSIONERS CURRITUCK TOWNSHIP"): (
        4, "nobody filed for this seat, so it is not in the 2022 filing list, "
           "and it was won by a declared write-in candidate; every other Hyde "
           "seat is a four-year term"),
}

# (county, seat group) -> why the next election's filing list disagrees with
# the seats this file names there. Measured 2026-10-11 against the 2026 list.
WITNESS_EXCEPTIONS = {
    ("WAKE", "WAKE COUNTY BOARD OF COMMISSIONERS AT-LARGE"):
        "two new at-large seats first elected in 2026 (S.L. 2023-30 enlarged "
        "the board); nobody holds them yet",
    ("WATAUGA", "WATAUGA COUNTY BOARD OF COMMISSIONERS DISTRICT 2"):
        "S.L. 2023-147 redrew Watauga's districts between the 2022 and 2024 "
        "elections, so the seats on the 2026 ballot carry the new map's labels",
    ("WATAUGA", "WATAUGA COUNTY BOARD OF COMMISSIONERS DISTRICT 4"):
        "S.L. 2023-147 redrew Watauga's districts between the 2022 and 2024 "
        "elections; the 2022 District 4 winner's term runs to December 2026 "
        "under the old map's label",
    ("HYDE", "HYDE COUNTY BOARD OF COMMISSIONERS CURRITUCK TOWNSHIP"):
        "the seat is on the 2026 ballot with nobody filed for it, so the "
        "filing list does not carry it (it was won by write-in in 2022 too)",
}

# Seat groups whose holders this file cannot settle from the results, with the
# reason. Each seat in the group names nobody. Measured 2026-10-11.
UNSETTLED_GROUPS = {
}

# Counties whose board elects three seats every cycle on a five-member board,
# the lowest-placed winner serving two years and the others four. The filing
# list gives every one of those seats a four-year term, so this is recorded:
# in each county the 2022 third-placed winner was on the 2024 ballot again
# and the 2026 filing list puts three seats on the ballot. Measured 2026-10-11;
# the next-election witness re-checks every entry on every run.
LAST_PLACE_SERVES_TWO = {"AVERY", "CLAY", "GRAHAM", "IREDELL", "YANCEY"}

# LIMITED VOTING. Five counties elect their boards by limited voting under
# federal consent decrees (NCACC's count, relayed in nc/WATCH.md): a voter
# marks fewer candidates than there are seats, so a contest's "vote for" is
# not its seat count and neither State Board file says how many seats it
# filled. Each contest below is recorded with the count the county's own
# board page gives, read 2026-10-11 with this project's own client; in every
# one the county's members are exactly the top vote-getters.
LIMITED_VOTING_SEATS = {
    (2022, "BEAUFORT", "BEAUFORT COUNTY BOARD OF COMMISSIONERS"): (
        3, "https://www.beaufortcountync.gov/294/Board-of-Commissioners"),
    (2024, "BEAUFORT", "BEAUFORT COUNTY BOARD OF COMMISSIONERS"): (
        4, "https://www.beaufortcountync.gov/294/Board-of-Commissioners"),
    (2022, "MARTIN", "MARTIN COUNTY BOARD OF COMMISSIONERS WESTERN DISTRICT"): (
        2, "https://www.martincountync.gov/government/county_commissioners/index.php"),
    (2024, "MARTIN", "MARTIN COUNTY BOARD OF COMMISSIONERS EASTERN DISTRICT"): (
        3, "https://www.martincountync.gov/government/county_commissioners/index.php"),
    (2022, "PERQUIMANS", "PERQUIMANS COUNTY BOARD OF COMMISSIONERS"): (
        3, "https://www.perquimanscountync.gov/board-of-commissioners"),
    (2024, "PERQUIMANS", "PERQUIMANS COUNTY BOARD OF COMMISSIONERS"): (
        3, "https://www.perquimanscountync.gov/board-of-commissioners"),
    # Tyrrell's site resets every HTTPS connection from this project's sandbox
    # and serves its pages over plain HTTP, which is how it was read on
    # 2026-10-15 (robots.txt read first: Joomla's default, which disallows
    # only its own system folders). Its board page names five commissioners:
    # the top two of 2022 and the top three of 2024, each contest "vote for 1".
    (2022, "TYRRELL", "TYRRELL COUNTY BOARD OF COMMISSIONERS"): (
        2, "http://tyrrellcounty.org/en/county-commissioner"),
    (2024, "TYRRELL", "TYRRELL COUNTY BOARD OF COMMISSIONERS"): (
        3, "http://tyrrellcounty.org/en/county-commissioner"),
}
# A limited-voting county whose seat counts could not be read, so its board
# names nobody. The fifth limited-voting county NCACC counts is not identified
# here: its table is behind a Cloudflare challenge (nc/WATCH.md).
LIMITED_VOTING_UNSETTLED = {}

# A note a seat needs that the results cannot carry, by (county, group, name).
SEAT_NOTES = {
    ("WATAUGA", "WATAUGA COUNTY BOARD OF COMMISSIONERS DISTRICT 4", "Larry Turnbow"):
        "Elected under the district map in force before S.L. 2023-147 redrew "
        "Watauga's districts; this term runs to December 2026.",
}


def fail(msg):
    raise SystemExit("build-nc-county-commissioners: FATAL: %s" % msg)


def general_day(year):
    """The Tuesday after the first Monday in November."""
    d = datetime.date(year, 11, 1)
    while d.weekday() != 0:
        d += datetime.timedelta(days=1)
    return d + datetime.timedelta(days=1)


def takes_office(year):
    """The first Monday in December after the election (NCGS 153A-26)."""
    d = datetime.date(year, 12, 1)
    while d.weekday() != 0:
        d += datetime.timedelta(days=1)
    return d


def group_of(contest):
    """One seat group's name across both years: the filing list and the
    results disagree about abbreviations ("BD OF", "DIST", "DISTRICT 04"),
    and an unexpired-term contest is the same seats as its regular one."""
    n = re.sub(r"\s*\(UNEXPIRED\)\s*$", "", contest.strip())
    n = re.sub(r" COUNTY (?:BD OF |)COMMISSIONERS", " COUNTY BOARD OF COMMISSIONERS", n)
    n = re.sub(r"\bDIST\b", "DISTRICT", n)
    n = re.sub(r"\bDISTRICT 0+(\d)", r"DISTRICT \1", n)
    n = re.sub(r"\bTWP\b", "TOWNSHIP", n)
    return re.sub(r"\s+", " ", n)


def seat_label(group):
    m = CONTEST_RE.match(group)
    rest = m.group("rest").strip(" -") if m else ""
    if not rest:
        return "Board seat"
    if rest in ("AT-LARGE", "AT LARGE", "COUNTY-WIDE", "COUNTYWIDE"):
        return "At large"
    if rest in ("CHAIRMAN", "CHAIR"):
        return "Chair"
    words = []
    for w in rest.split():
        if re.fullmatch(r"[IVX]+", w):
            words.append(w)
        else:
            words.append(w[:1] + w[1:].lower())
    return " ".join(words).replace("At-large", "At large")


def county_geoids():
    with open(COUNTIES_FILE, encoding="utf-8") as f:
        feats = json.load(f)["features"]
    out = {}
    for feat in feats:
        p = feat["properties"]
        out[str(p["BASENAME"])] = str(p["GEOID"])
    if len(out) != EXPECT_COUNTIES:
        fail("the shipped county layer draws %d counties, expected %d"
             % (len(out), EXPECT_COUNTIES))
    return out


def results_county(upper, geoids):
    key = re.sub(r"[^A-Z]", "", upper.upper())
    for name in geoids:
        if re.sub(r"[^A-Z]", "", name.upper()) == key:
            return name
    fail("the results name a county %r the map does not draw" % upper)


def fetch(url):
    import requests
    require_robots_once(url, UA_ROSTER_BOT, headers=UA_HEADERS_ROSTER_BOT)
    r = requests.get(url, headers=UA_HEADERS_ROSTER_BOT, timeout=REQUEST_TIMEOUT)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.content


def generals_in_office(today):
    """Every even-year general from FIRST_YEAR whose winners have taken office."""
    years = []
    y = FIRST_YEAR
    while takes_office(y) <= today:
        years.append(y)
        y += 2
    return years


def read_results(year):
    day = general_day(year)
    url = RESULTS_ZIP % (day.strftime("%Y_%m_%d"), day.strftime("%Y%m%d"))
    body = fetch(url)
    if body is None:
        return None, url
    with zipfile.ZipFile(io.BytesIO(body)) as z:
        names = [n for n in z.namelist() if n.lower().endswith(".txt")]
        if len(names) != 1:
            fail("%s holds %d text files, expected one" % (url, len(names)))
        text = z.read(names[0]).decode("latin-1")
    votes = collections.defaultdict(collections.Counter)
    vote_for = {}
    for row in csv.DictReader(io.StringIO(text), delimiter="\t"):
        name = row["Contest Name"].strip()
        m = CONTEST_RE.match(name)
        if not m or "REFERENDUM" in name:
            continue
        if re.sub(r"[^A-Z]", "", m.group("county")) != re.sub(r"[^A-Z]", "", row["County"]):
            continue
        key = (row["County"].strip(), name)
        votes[key][(row["Choice"].strip(), row["Choice Party"].strip())] += int(row["Total Votes"] or 0)
        vote_for[key] = int(row["Vote For"])
    return (votes, vote_for), url


def read_filings(year):
    """(county, contest) -> (term, unexpired, vote_for) for the general of
    `year`, from that year's candidate filing list. Only the contest columns
    are read: the list also carries every candidate's home address, which this
    project never publishes."""
    body = fetch(CANDIDATES % (year, year))
    if body is None:
        return None
    want = general_day(year).strftime("%m/%d/%Y")
    out = {}
    for row in csv.DictReader(io.StringIO(body.decode("latin-1"))):
        if row["election_dt"] != want:
            continue
        name = row["contest_name"].strip()
        if not CONTEST_RE.match(name) or "REFERENDUM" in name:
            continue
        out[(row["county_name"].strip(), name)] = (
            int(row["term"]), row["is_unexpired"] == "TRUE", int(row["vote_for"]))
    return out


def winners(counter, vote_for):
    """The vote_for most-voted choices, or None for a seat a tie decides."""
    ranked = sorted(counter.items(), key=lambda kv: -kv[1])
    out = []
    for i in range(vote_for):
        if i >= len(ranked):
            out.append(None)
            continue
        (choice, party), n = ranked[i]
        if n == 0:
            out.append(None)
            continue
        tied = (i + 1 < len(ranked) and ranked[i + 1][1] == n and i + 1 >= vote_for) or \
               (i > 0 and ranked[i - 1][1] == n and i >= vote_for)
        out.append(None if tied else (choice, party))
    return out


def person(choice, party, year, url):
    rec = {"election": general_day(year).isoformat(), "sourceUrl": url}
    if choice is None:
        rec["unnamed"] = "the results do not settle this seat (a tie)"
        return rec
    m = re.fullmatch(r"(.+?)\s*\(Write-In\)", choice)
    if choice.startswith("Write-In (Miscellaneous)"):
        rec["unnamed"] = ("won by write-in votes the results do not attribute "
                          "to anybody")
        return rec
    rec["name"] = m.group(1).strip() if m else choice
    if m:
        rec["writeIn"] = True
    if party in PARTY_NAMES:
        rec["party"] = PARTY_NAMES[party]
    return rec


def build(today):
    geoids = county_geoids()
    years = generals_in_office(today)[-2:]
    if len(years) < 2:
        fail("fewer than two generals in office by %s" % today)
    newest = years[-1]
    seats = collections.defaultdict(list)   # (county, group) -> [record]
    replaced = collections.Counter()         # group -> unexpired winners not paired
    used_limited = set()
    for year in years:
        res, url = read_results(year)
        if res is None:
            fail("no results file for the %d general at %s" % (year, url))
        votes, vote_for = res
        filings = read_filings(year)
        if filings is None:
            fail("no candidate filing list for %d" % year)
        page = RESULTS_PAGE % general_day(year).strftime("%m/%d/%Y")
        for key in sorted(votes):
            county, contest = key
            if key in filings:
                term, unexpired, vf = filings[key]
                if vf != vote_for[key]:
                    fail("%r: the filing list says vote for %d, the results %d"
                         % (key, vf, vote_for[key]))
            elif (year,) + key in DECLARED_TERMS:
                term, unexpired = DECLARED_TERMS[(year,) + key][0], False
            else:
                fail("%d %r is in the results and not in the filing list; "
                     "measure it and record it in DECLARED_TERMS" % (year, key))
            group = (county, group_of(contest))
            if county in LIMITED_VOTING_UNSETTLED:
                seats[group] = [{"unnamed": LIMITED_VOTING_UNSETTLED[county],
                                 "_year": None, "_end": None, "_limited": True}]
                continue
            n_seats = vote_for[key]
            if (year,) + key in LIMITED_VOTING_SEATS:
                n_seats = LIMITED_VOTING_SEATS[(year,) + key][0]
                used_limited.add((year,) + key)
            got = [person(c[0] if c else None, c[1] if c else "", year, page)
                   for c in winners(votes[key], n_seats)]
            for g in got:
                g["_limited"] = n_seats != vote_for[key]
            if unexpired:
                end = year + 2
                prior = [r for r in seats[group] if r["_year"] < year and r["_end"] > year]
                if len(prior) == 1:
                    seats[group].remove(prior[0])
                elif prior:
                    names = ", ".join(r.get("name", "nobody") for r in prior)
                    replaced[group] += len(got)
                    for r in prior:
                        r.setdefault("notes", []).append(
                            "One of the people elected to these seats on %s (%s) "
                            "left the board before %s, when %s won the rest of "
                            "that term; the results do not say which one."
                            % (_long(r["election"]), names, _long(general_day(year).isoformat()),
                               " and ".join(g.get("name", "nobody") for g in got)))
            else:
                end = year + term
            for i, rec in enumerate(got):
                rec["_year"], rec["_end"] = year, end
                if not unexpired and county in LAST_PLACE_SERVES_TWO and \
                        vote_for[key] > 1 and i == vote_for[key] - 1:
                    rec["_end"] = year + 2
                    rec["shortTerm"] = True
                if unexpired:
                    rec["unexpiredTerm"] = True
                seats[group].append(rec)
    unused = set(LIMITED_VOTING_SEATS) - used_limited
    if unused:
        fail("LIMITED_VOTING_SEATS names contests the results do not carry: %r"
             % sorted(unused))
    # Current seats only.
    for group in list(seats):
        seats[group] = [r for r in seats[group]
                        if r.get("_limited") and r["_end"] is None or r["_end"] > newest]
        if not seats[group]:
            del seats[group]
    # The same person winning twice in one county keeps the newer win.
    by_person = collections.defaultdict(list)
    for group, recs in seats.items():
        for r in recs:
            if r.get("name"):
                by_person[(group[0], r["name"].lower())].append((group, r))
    for (county, _), hits in by_person.items():
        if len(hits) < 2:
            continue
        hits.sort(key=lambda gr: gr[1]["_year"])
        later_group, later = hits[-1]
        for group, r in hits[:-1]:
            if group == later_group:
                seats[group].remove(r)
                continue
            # A second seat cannot be held with the first, so the first is
            # vacant or appointed, which no result records.
            left = r.pop("name")
            r.pop("party", None)
            r.pop("writeIn", None)
            r["unnamed"] = ("%s won this seat on %s and then won the %s seat on %s, "
                            "so has left this one. Whoever the board appointed is "
                            "in no election result." % (left, _long(r["election"]),
                                                        seat_label(later_group[1]),
                                                        _long(later["election"])))
    for group, why in UNSETTLED_GROUPS.items():
        if [r for r in seats.get(group, []) if r.get("name")]:
            fail("UNSETTLED_GROUPS names %r, which the results now settle" % (group,))
        seats[group] = [{"unnamed": why, "_year": None, "_end": newest + 2}]
    for (county, group, who), note in SEAT_NOTES.items():
        hit = [r for r in seats.get((county, group), []) if r.get("name") == who]
        if len(hit) != 1:
            fail("SEAT_NOTES names %s in %r, who is not there once" % (who, group))
        hit[0].setdefault("notes", []).append(note)
    # The next general's filing list.
    witness_year = newest + 2
    filings = read_filings(witness_year)
    witness = {"year": witness_year, "checked": filings is not None}
    if filings is None:
        print("note: no %d filing list yet; the next-election witness is skipped"
              % witness_year)
    else:
        up = collections.Counter()
        unexp = collections.defaultdict(int)
        for (county, contest), (term, unexpired, vf) in filings.items():
            g = (county, group_of(contest))
            if unexpired:
                unexp[g] += vf
            else:
                up[g] += vf
        ending = collections.Counter()
        for g, recs in seats.items():
            ending[g] = sum(1 for r in recs if r["_end"] == witness_year) - replaced[g]
        problems = []
        for g in sorted(set(up) | {g for g, n in ending.items() if n}):
            if up[g] == ending[g]:
                if g in WITNESS_EXCEPTIONS:
                    problems.append("%r agrees with the %d filing list now; retire "
                                    "its WITNESS_EXCEPTIONS entry" % (g, witness_year))
                continue
            if any(r.get("_limited") for r in seats.get(g, [])):
                print("witness skipped for %r: limited voting, so the filing list's "
                      "vote-for count is not a seat count" % (g,))
                continue
            if g in WITNESS_EXCEPTIONS:
                print("witness exception %r: %s" % (g, WITNESS_EXCEPTIONS[g]))
                continue
            problems.append("%r: %d seats here end in %d and the %d filing list "
                            "has %d on the ballot" % (g, ending[g], witness_year,
                                                       witness_year, up[g]))
        for g, n in sorted(unexp.items()):
            later = [r for r in seats.get(g, []) if r["_end"] > witness_year and r.get("name")]
            if not later:
                problems.append("%r has an unexpired-term contest on the %d ballot "
                                "and no later-ending winner here" % (g, witness_year))
                continue
            when = _long(general_day(witness_year).isoformat())
            if len(later) == n:
                for r in later:
                    left = r.pop("name")
                    r.pop("party", None)
                    r.pop("writeIn", None)
                    r["unnamed"] = ("%s won this seat on %s and has since left it: "
                                    "the rest of the term is on the %s ballot. "
                                    "Whoever the board appointed meanwhile is in no "
                                    "election result." % (left, _long(r["election"]), when))
            else:
                names = ", ".join(r["name"] for r in later)
                for r in later:
                    r.setdefault("notes", []).append(
                        "%d of these seats (%s) changed hands after the election: "
                        "the rest of %s is on the %s ballot, and the results do "
                        "not say whose seat it was." % (n, names,
                                                        "that term" if n == 1 else "those terms",
                                                        when))
        if problems:
            fail("next-election witness:\n  " + "\n  ".join(problems))
        for g in WITNESS_EXCEPTIONS:
            if g not in up and not ending.get(g):
                fail("WITNESS_EXCEPTIONS names %r, which neither side carries" % (g,))
    # Assemble, keyed by GEOID.
    out = {}
    for (county, group), recs in sorted(seats.items()):
        name = results_county(county, geoids)
        rec = out.setdefault(geoids[name], {"county": name, "seats": []})
        label = seat_label(group)
        for r in recs:
            seat = {"seat": label}
            for k in ("name", "party", "election", "writeIn", "unexpiredTerm", "shortTerm",
                      "unnamed", "sourceUrl"):
                if r.get(k) is not None:
                    seat[k] = r[k]
            if r.get("_end"):
                seat["termEnds"] = takes_office(r["_end"]).isoformat()
            if r.get("notes"):
                seat["note"] = " ".join(r["notes"])
            rec["seats"].append(seat)
    for rec in out.values():
        rec["seats"].sort(key=_seat_order)
    return out, years, witness


def _seat_order(s):
    m = re.search(r"(\d+)", s["seat"])
    return (s["seat"] == "Chair" and -1 or 0, re.sub(r"\d+", "", s["seat"]),
            int(m.group(1)) if m else 0, s.get("name") or "")


def _long(iso):
    if not iso:
        return "an earlier election"
    d = datetime.date.fromisoformat(iso)
    return "%s %d, %d" % (d.strftime("%B"), d.day, d.year)


def check(data):
    geoids = county_geoids()
    problems = []
    want = set(geoids.values())
    have = {k for k in data if not k.startswith("_")}
    if have != want:
        problems.append("counties missing: %s; unexpected: %s"
                        % (sorted(want - have), sorted(have - want)))
    named = 0
    for geoid in sorted(have & want):
        rec = data[geoid]
        if rec.get("county") not in geoids or geoids[rec["county"]] != geoid:
            problems.append("%s carries county %r" % (geoid, rec.get("county")))
        if not rec.get("seats"):
            problems.append("%s County lists no seats" % rec.get("county"))
        for s in rec.get("seats", []):
            if bool(s.get("name")) == bool(s.get("unnamed")):
                problems.append("%s County %r must carry exactly one of name and "
                                "unnamed" % (rec.get("county"), s.get("seat")))
            if s.get("name"):
                named += 1
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(s.get("election"))):
                    problems.append("%s County %s names %r with no election date"
                                    % (rec.get("county"), s.get("seat"), s["name"]))
                if re.search(r"write-in|\d{3}", s["name"], re.I):
                    problems.append("%s County: %r is not a name"
                                    % (rec.get("county"), s["name"]))
    if named < MIN_NAMED:
        problems.append("%d named seats, below the floor of %d" % (named, MIN_NAMED))
    if problems:
        fail("\n  " + "\n  ".join(problems))
    print("build-nc-county-commissioners --check: OK — %d counties, %d named seats, "
          "%d seats naming nobody" % (len(have), named,
                                      sum(1 for k in have for s in data[k]["seats"]
                                          if s.get("unnamed"))))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="offline: hold the shipped file to the shipped county layer")
    args = ap.parse_args()
    if args.check:
        with open(OUT_FILE, encoding="utf-8") as f:
            check(json.load(f))
        return
    today = datetime.date.today()
    data, years, witness = build(today)
    data["_meta"] = {
        "source": "North Carolina State Board of Elections: certified precinct "
                  "results and candidate filing lists (dl.ncsbe.gov)",
        "generals": [general_day(y).isoformat() for y in years],
        "witness": ("the %d candidate filing list" % witness["year"]
                    if witness["checked"] else None),
    }
    check(data)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, sort_keys=True, ensure_ascii=False)
        f.write("\n")
    print("wrote %s" % os.path.relpath(OUT_FILE))


if __name__ == "__main__":
    main()
