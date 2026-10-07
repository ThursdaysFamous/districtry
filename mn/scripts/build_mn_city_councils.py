#!/usr/bin/env python3
"""The mayor and council of each Minnesota city above 25,000 people, from the
Secretary of State's own election results, every name dated to the election
that seated it.

WHAT THIS PUBLISHES AND WHAT IT DOES NOT. The Secretary of State publishes the
result of every city contest it reports as a plain text file per election day
(`local.txt`, under electionresultsfiles.sos.mn.gov/<YYYYMMDD>/), the same host
and shape `build_mn_commissioner_roster.py` reads for county commissioners. A
winner is a fact with a date on it. It is NOT a statement of who holds the seat
today: a council member who has resigned, or been replaced by appointment since,
still shows here as the person who won. So every record names its election, and
the card says so in words — the certified-returns posture the commissioner
roster ships under.

WHICH CITIES. The 43 the done standard counts (docs/expected-governments.json,
Census 2020 population of 25,000 or more), joined by the place code the results
file carries in its sixth field, which is the last five digits of the city's
Census id. The other 813 cities are a later change, and the gap record says so.

A SEAT IS A COUNT, NOT A NAME, AND THE COUNT IS DECLARED. The results file
names an office ("Council Member Ward 1 (Blaine)") and how many it elects that
day ("(Elect 2)"), never how many seats share that office. Blaine elects two
members per ward in alternate years, so "Ward 1" in 2022 and in 2024 is two
seats; Minneapolis elects one member per ward, and its 2023 and 2025 contests
for Ward 1 are the same seat. Nothing in the file tells those apart, so SEATS
below states how many seats each office has, measured from the election pattern
and checked against each city's own council page (2026-10-07, recorded in
mn/WATCH.md). A city's declared seats must add up to the council size it
publishes, and an office the results name that SEATS does not declare fails the
build, so a city that redraws its wards cannot slip past the table.

HOW A SEAT IS FILLED. For each office, the counting contests are walked newest
first, and each fills as many seats as it elected:
  * A regular general fills its seats. If it elected more winners than seats
    are left, the results cannot say which of them still sit, so the seats left
    name nobody and say why.
  * A special general held on the SAME DAY as a regular one for the same office
    filled the OTHER seat — the one whose regular election comes next — so it
    counts only if no later regular election for that office has happened.
  * A special general on its own day filled a seat whose term the results do
    not give. If a regular election for that office followed it, the special's
    seat may already have been re-elected or may not, and the seats left name
    nobody.
  * A special PRIMARY after the newest general for an office means a seat is
    changing hands now. That seat names nobody until the special's general is
    canvassed.

FIVE WAYS A CONTEST IS NOT A WINNER, the commissioner roster's four plus one:
a primary (a general carries a WRITE-IN line and a primary does not, measured on
every file this reads), a contest not yet CANVASS_DAYS old, a seat won by
write-in, a tie at the last seat, and — new here — RANKED-CHOICE VOTING.
Minneapolis, St. Paul, Bloomington, Minnetonka and St. Louis Park count ranked
ballots, and the state's file carries the first-choice count only (2023 also
carries second and third choices, unredistributed). A candidate is named only
where first choices alone decide it: a majority for one seat, or the
Droop quota for several. Anywhere else the seat names nobody, because the
city's own round-by-round count decides it and this file does not carry it, and
taking the first-choice leader would be a guess.

Usage:
    python3 mn/scripts/build_mn_city_councils.py          # fetch and write
    python3 mn/scripts/build_mn_city_councils.py --check  # offline gate
    python3 mn/scripts/build_mn_city_councils.py --cache DIR   # read saved local.txt files
"""

import argparse
import datetime
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
REPO = os.path.dirname(INSTANCE)
FLEET_SCRIPTS = os.path.join(REPO, "scripts")
sys.path.insert(0, FLEET_SCRIPTS)

FILES_HOST = "https://electionresultsfiles.sos.mn.gov"
RESULTS_FILE = FILES_HOST + "/%s/local.txt"
USER_AGENT = "districtry/1.0 (+https://districtry.com/mn/)"
REQUEST_TIMEOUT = 60
PACE_SECONDS = 0.5
FIRST_ELECTION = datetime.date(2022, 11, 8)
CANVASS_DAYS = 21

EXPECTED = os.path.join(REPO, "docs", "expected-governments.json")
OUT_FILE = os.path.join(INSTANCE, "data", "app", "mn-city-councils.json")
STATE_FIPS = "27"

# Cities that count ranked ballots. The results file says so too (its office
# names carry "First Choice"); this list is the check that it still does.
RANKED_CHOICE = {"2743000", "2758000", "2706616", "2743252", "2757220"}

# How many seats each office has, by city (see the module docstring). The
# mayor is one seat everywhere. "At Large" covers both "Council Member at Large"
# and a plain "Council Member (City) (Elect N)", which the files use for the
# same seats in different years (Cottage Grove 2022 and 2024).
#
# Measured 2026-10-07. Each office's count is the seats its regular elections
# filled across one four-year cycle (2022 + 2024, or 2023 + 2025), which is the
# council when terms are four years and staggered — and it is NOT for three
# cities, where the same single seat was elected twice: Minneapolis elected
# every ward for two years in 2023 and for four in 2025; Bloomington elected
# every seat in 2023 under its new ward plan, some for two years; and Duluth
# District 4 was on both ballots. Those three are stated by hand. The other 40
# follow the cycle, and 33 of the 43 cities' own council pages, read the same
# day, give the same council size (mn/WATCH.md); the remaining ten refused this
# client (an Akamai or Cloudflare block, or a robots refusal) and were not read
# any other way.
SEATS = {
    "2701486": {"Mayor": 1, "At Large": 4},  # Andover
    "2701900": {"Mayor": 1, "At Large": 4},  # Apple Valley
    "2702908": {"Mayor": 1, "At Large": 1, "Ward 1": 2, "Ward 2": 2, "Ward 3": 2},  # Austin
    "2706382": {"Mayor": 1, "Ward 1": 2, "Ward 2": 2, "Ward 3": 2},  # Blaine
    "2706616": {"Mayor": 1, "At Large": 2, "Ward 1": 1, "Ward 2": 1, "Ward 3": 1, "Ward 4": 1},  # Bloomington
    "2707948": {"Mayor": 1, "At Large": 4},  # Brooklyn Center
    "2707966": {"Mayor": 1, "Ward C": 2, "Ward E": 2, "Ward W": 2},  # Brooklyn Park
    "2708794": {"Mayor": 1, "At Large": 4},  # Burnsville
    "2710918": {"Mayor": 1, "At Large": 4},  # Chanhassen
    "2710972": {"Mayor": 1, "Ward 1": 1, "Ward 2": 1, "Ward 3": 1, "Ward 4": 1},  # Chaska
    "2713114": {"Mayor": 1, "At Large": 1, "Ward 1": 1, "Ward 2": 1, "Ward 3": 1, "Ward 4": 1, "Ward 5": 1},  # Coon Rapids
    "2713456": {"Mayor": 1, "At Large": 4},  # Cottage Grove
    "2717000": {"Mayor": 1, "At Large": 4, "District 1": 1, "District 2": 1, "District 3": 1, "District 4": 1, "District 5": 1},  # Duluth
    "2717288": {"Mayor": 1, "At Large": 4},  # Eagan
    "2718116": {"Mayor": 1, "At Large": 4},  # Eden Prairie
    "2718188": {"Mayor": 1, "At Large": 4},  # Edina
    "2718674": {"Mayor": 1, "Ward 1": 1, "Ward 2": 1, "Ward 3": 1, "Ward 4": 1},  # Elk River
    "2722814": {"Mayor": 1, "At Large": 1, "Ward 1": 1, "Ward 2": 1, "Ward 3": 1},  # Fridley
    "2731076": {"Mayor": 1, "At Large": 4},  # Inver Grove Heights
    "2735180": {"Mayor": 1, "At Large": 4},  # Lakeville
    "2739878": {"Mayor": 1, "At Large": 1, "Ward 1": 1, "Ward 2": 1, "Ward 3": 1, "Ward 4": 1, "Ward 5": 1},  # Mankato
    "2740166": {"Mayor": 1, "At Large": 4},  # Maple Grove
    "2740382": {"Mayor": 1, "At Large": 4},  # Maplewood
    "2743000": {"Mayor": 1, "Ward 1": 1, "Ward 2": 1, "Ward 3": 1, "Ward 4": 1, "Ward 5": 1, "Ward 6": 1, "Ward 7": 1, "Ward 8": 1, "Ward 9": 1, "Ward 10": 1, "Ward 11": 1, "Ward 12": 1, "Ward 13": 1},  # Minneapolis
    "2743252": {"Mayor": 1, "Seat A": 1, "Seat B": 1, "Ward 1": 1, "Ward 2": 1, "Ward 3": 1, "Ward 4": 1},  # Minnetonka
    "2743864": {"Mayor": 1, "Ward 1": 2, "Ward 2": 2, "Ward 3": 2, "Ward 4": 2},  # Moorhead
    "2747680": {"Mayor": 1, "At Large": 4},  # Oakdale
    "2749300": {"Mayor": 1, "At Large": 2, "Ward 1": 1, "Ward 2": 1, "Ward 3": 1, "Ward 4": 1, "Ward 5": 1},  # Owatonna
    "2751730": {"Mayor": 1, "At Large": 2, "Ward 1": 1, "Ward 2": 1, "Ward 3": 1, "Ward 4": 1},  # Plymouth
    "2752594": {"Mayor": 1, "At Large": 4},  # Prior Lake
    "2753026": {"Mayor": 1, "At Large": 2, "Ward 1": 1, "Ward 2": 1, "Ward 3": 1, "Ward 4": 1},  # Ramsey
    "2754214": {"Mayor": 1, "At Large": 1, "Ward 1": 1, "Ward 2": 1, "Ward 3": 1},  # Richfield
    "2754880": {"Mayor": 1, "At Large": 1, "District 1": 1, "District 2": 1, "District 3": 1, "District 4": 1, "District 5": 1, "District 6": 1},  # Rochester
    "2755726": {"Mayor": 1, "At Large": 4},  # Rosemount
    "2755852": {"Mayor": 1, "At Large": 4},  # Roseville
    "2758738": {"Mayor": 1, "At Large": 4},  # Savage
    "2759350": {"Mayor": 1, "At Large": 4},  # Shakopee
    "2759998": {"Mayor": 1, "At Large": 4},  # Shoreview
    "2756896": {"Mayor": 1, "At Large": 3, "Ward 1": 1, "Ward 2": 1, "Ward 3": 1, "Ward 4": 1},  # St. Cloud
    "2757220": {"Mayor": 1, "Seat A": 1, "Seat B": 1, "Ward 1": 1, "Ward 2": 1, "Ward 3": 1, "Ward 4": 1},  # St. Louis Park
    "2758000": {"Mayor": 1, "Ward 1": 1, "Ward 2": 1, "Ward 3": 1, "Ward 4": 1, "Ward 5": 1, "Ward 6": 1, "Ward 7": 1},  # St. Paul
    "2771032": {"Mayor": 1, "At Large": 2, "Ward 1": 1, "Ward 2": 1, "Ward 3": 1, "Ward 4": 1},  # Winona
    "2771428": {"Mayor": 1, "At Large": 4},  # Woodbury
}

# Where a city's own council page, read 2026-10-07, names somebody else for a
# seat than the results file's winner. Read once and dated, not re-fetched:
# ten of the 43 cities' sites refuse this client, and a weekly scrape of 33
# differently built pages would break weekly. 196 of the 199 named seats those
# 33 pages could be compared on agree; these are the three that do not, each a
# seat filled since by appointment by the look of the page. Each entry names
# the results winner it was read against, and it FAILS once that seat names
# anybody else, so a later election cannot leave a stale note behind.
CITY_PAGE_SAYS = {
    ("2702908", "Ward 3", "Joyce Poshusta"): (
        "Oballa Oballa", "https://www.ci.austin.mn.us/city-council"),
    ("2722814", "Ward 1", "Tom Tillberry"): (
        "Luke Cardona",
        "https://www.fridleymn.gov/Your-Government/City-Council-Commissions/"
        "Meet-Your-City-Council"),
    ("2747680", "At Large", "Susan Olson"): (
        "Katie Wrich", "https://www.oakdalemn.gov/317/City-Council"),
}
CITY_PAGES_READ = "2026-10-07"

OFFICE_RE = re.compile(
    r"^(?P<special>Special Election for )?"
    r"(?P<office>Mayor|Council Member)"
    r"(?: (?P<kind>Ward|District|Seat) (?P<label>\w+)| (?P<large>at Large))?"
    r"(?: (?P<choice>First|Second|Third) Choice)?"
    r" \((?P<city>[^)]+)\)"
    r"(?: \(Elect (?P<elect>\d+)\))?"
    r"(?P<sprimary> \(Special Primary\))?$", re.I)


def fail(msg):
    raise SystemExit("build-mn-city-councils: FATAL: %s" % msg)


def cities():
    with open(EXPECTED, encoding="utf-8") as fh:
        units = json.load(fh)["units"]["mn"]
    out = {}
    for u in units:
        if u["kind"] != "place" or not u["geoid"].startswith(STATE_FIPS):
            fail("expected-governments lists %r for Minnesota, which is not a "
                 "Minnesota place" % u)
        out[u["geoid"]] = re.sub(r" city$", "", u["name"])
    return out


def fetch_elections(session, today):
    """{date: text} for every Tuesday since FIRST_ELECTION whose results
    directory carries a local races file."""
    from scraper_common import require_robots_once  # noqa: PLC0415
    require_robots_once(RESULTS_FILE % FIRST_ELECTION.strftime("%Y%m%d"), USER_AGENT)
    out = {}
    day = FIRST_ELECTION
    while day <= today:
        url = RESULTS_FILE % day.strftime("%Y%m%d")
        resp = session.get(url, headers={"User-Agent": USER_AGENT},
                           timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            out[day] = resp.content.decode("latin-1")
        elif resp.status_code != 404:
            fail("%s answered HTTP %d — a probe that cannot tell an empty day "
                 "from a failure must stop" % (url, resp.status_code))
        time.sleep(PACE_SECONDS)
        day += datetime.timedelta(days=7)
    if FIRST_ELECTION not in out:
        fail("the 2022 general's local results file is missing")
    return out


def read_cache(folder):
    out = {}
    for name in sorted(os.listdir(folder)):
        m = re.match(r"^(\d{8})\.txt$", name)
        if m:
            day = datetime.datetime.strptime(m.group(1), "%Y%m%d").date()
            with open(os.path.join(folder, name), encoding="latin-1") as fh:
                out[day] = fh.read()
    return out


def seat_key(m):
    if m.group("office").lower() == "mayor":
        return "Mayor"
    if m.group("kind"):
        return "%s %s" % (m.group("kind").title(), m.group("label").upper()
                          if len(m.group("label")) == 1 and m.group("label").isalpha()
                          else m.group("label"))
    return "At Large"


def contests(elections, wanted):
    """Every mayor and council contest in the wanted cities, oldest first."""
    found = []
    codes = {g[2:]: g for g in wanted}
    for day in sorted(elections):
        groups = {}
        for line in elections[day].splitlines():
            if not line.strip():
                continue
            f = line.split(";")
            if len(f) < 16:
                fail("%s: a line with %d fields: %r" % (day, len(f), line[:120]))
            geoid = codes.get(f[5].strip())
            if geoid is None:
                continue
            m = OFFICE_RE.match(f[4].strip())
            if not m:
                continue
            groups.setdefault((geoid, f[4].strip()), (m, []))[1].append(f)
        for (geoid, office), (m, rows) in sorted(groups.items()):
            choice = (m.group("choice") or "").lower()
            if choice in ("second", "third"):
                continue
            found.append({
                "date": day, "geoid": geoid, "office": office,
                "key": seat_key(m), "special": bool(m.group("special")),
                "labelled_primary": bool(m.group("sprimary")),
                "rcv": bool(choice), "elect": int(m.group("elect") or 1),
                "candidates": [(r[7].strip(), int(r[13])) for r in rows],
            })
    return found


def is_general(c):
    return (not c["labelled_primary"]
            and any(n.upper() == "WRITE-IN" for n, _ in c["candidates"]))


def winners(c):
    """[(name or None, why)] for each seat this contest filled."""
    k = c["elect"]
    cands = sorted(c["candidates"], key=lambda x: -x[1])
    if c["rcv"]:
        total = sum(v for _, v in cands)
        quota = total / 2.0 if k == 1 else total // (k + 1) + 1
        out = []
        for name, votes in cands:
            if len(out) == k:
                break
            if (votes > quota if k == 1 else votes >= quota) and name.upper() != "WRITE-IN":
                out.append((name, None))
        why = ("no candidate won on first choices alone; the city's own "
               "ranked-choice count decides this seat and the state's results "
               "file carries first choices only")
        return out + [(None, why)] * (k - len(out))
    out = []
    for i in range(k):
        if i >= len(cands):
            out.append((None, "the contest had fewer candidates than seats"))
            continue
        name, votes = cands[i]
        if any(v == votes for _, v in cands[k:]):
            out.append((None, "the published result is a tie at the last seat, "
                              "which Minnesota breaks by lot"))
        elif name.upper() == "WRITE-IN":
            out.append((None, "won by write-in votes, which the results do not name"))
        else:
            out.append((name, None))
    return out


def fill(geoid, key, seats, events, today):
    """The seats of one office, newest contest first. Returns a list of seat
    records, each naming a person or saying why it names nobody."""
    gens = [c for c in events if is_general(c)]
    held = [c for c in gens if (today - c["date"]).days < CANVASS_DAYS]
    gens = [c for c in gens if c not in held]
    regular_dates = sorted({c["date"] for c in gens if not c["special"]})
    newest_general = max([c["date"] for c in gens] or [datetime.date.min])
    out = []

    def unnamed(why, n):
        for _ in range(n):
            out.append({"unnamed": why})

    pending = [c for c in events
               if c["special"] and not is_general(c) and c["date"] > newest_general]
    for c in held:
        if len(out) < seats:
            unnamed("the %s election is not yet canvassed" % c["date"].isoformat(),
                    min(c["elect"], seats - len(out)))
    if pending and len(out) < seats:
        unnamed("a special election for this seat is under way (primary held %s)"
                % pending[0]["date"].isoformat(), 1)
    order = sorted(gens, key=lambda c: (c["date"], not c["special"]), reverse=True)
    for c in order:
        left = seats - len(out)
        if left <= 0:
            break
        later_regular = any(d > c["date"] for d in regular_dates)
        if c["special"]:
            same_day = c["date"] in regular_dates
            if same_day and later_regular:
                continue  # its seat has been re-elected since
            if not same_day and later_regular:
                unnamed("a special election on %s filled one of these seats and "
                        "the results cannot say which, nor whether a later "
                        "regular election re-elected it" % c["date"].isoformat(),
                        left)
                break
        got = winners(c)
        if len(got) > left:
            unnamed("the %s election filled %d of these seats and the results "
                    "cannot say which of its winners still holds the %d left"
                    % (c["date"].isoformat(), len(got), left), left)
            break
        for name, why in got:
            rec = {"election": c["date"].isoformat(),
                   "sourceUrl": RESULTS_FILE % c["date"].strftime("%Y%m%d")}
            if c["special"]:
                rec["special"] = True
            if name:
                rec["name"] = name
            else:
                rec["unnamed"] = why
            out.append(rec)
    left = seats - len(out)
    if left > 0:
        unnamed("no contest for this seat appears in any results file the "
                "Secretary of State published since the %s general"
                % FIRST_ELECTION.isoformat(), left)
    for rec in out:
        rec["seat"] = key
    return out


def vacate_moved(seats):
    """A person who won a seat and later won a different seat in the same
    city has left the first one (measured 2026-10-07: Andover, Minnetonka and
    St. Cloud each elected a council member mayor). The results cannot say who
    holds the seat they left, so it names nobody and says why."""
    named = [x for x in seats if x.get("name")]
    left = []
    for rec in named:
        later = [x for x in named if x is not rec
                 and x["name"].lower() == rec["name"].lower()
                 and x["election"] > rec["election"]]
        if later:
            left.append((rec, max(later, key=lambda x: x["election"])))
    for rec, moved in left:
        what = "mayor" if moved["seat"] == "Mayor" else "to the %s seat" % moved["seat"]
        rec["unnamed"] = ("%s, who won this seat on %s, was elected %s on %s, "
                          "and the results do not say who holds this seat now"
                          % (rec.pop("name"), rec["election"], what,
                             moved["election"]))


def build(found, wanted, today):
    by = {}
    for c in found:
        by.setdefault(c["geoid"], {}).setdefault(c["key"], []).append(c)
    roster = {}
    for geoid, name in sorted(wanted.items()):
        declared = SEATS.get(geoid)
        if declared is None:
            fail("%s (%s) has no SEATS entry" % (name, geoid))
        offices = by.get(geoid, {})
        extra = sorted(set(offices) - set(declared))
        if extra:
            fail("%s: the results name %s, which SEATS does not declare — a "
                 "redrawn ward map or a new seat; re-measure the city"
                 % (name, ", ".join(extra)))
        rcv = any(c["rcv"] for v in offices.values() for c in v)
        if rcv != (geoid in RANKED_CHOICE):
            fail("%s: ranked-choice is %s in the results and %s in RANKED_CHOICE"
                 % (name, rcv, geoid in RANKED_CHOICE))
        seats = []
        for key, n in declared.items():
            seats.extend(fill(geoid, key, n, offices.get(key, []), today))
        vacate_moved(seats)
        for (g, key, winner_name), (theirs, url) in CITY_PAGE_SAYS.items():
            if g != geoid:
                continue
            hit = [x for x in seats if x["seat"] == key and x.get("name") == winner_name]
            if len(hit) != 1:
                fail("CITY_PAGE_SAYS: %s %s no longer names %s, so the city "
                     "page's %s (read %s) describes a seat this file does not "
                     "carry — re-read the city's page and drop or replace the "
                     "entry" % (name, key, winner_name, theirs, CITY_PAGES_READ))
            hit[0]["citySays"] = {"name": theirs, "read": CITY_PAGES_READ,
                                  "sourceUrl": url}
        roster[geoid] = {"name": name, "rankedChoice": rcv, "seats": seats}
    return roster


def check(roster, wanted):
    problems = []
    if set(roster) != set(wanted):
        problems.append("the roster's cities differ from expected-governments: "
                        "missing %s, extra %s" % (sorted(set(wanted) - set(roster)),
                                                   sorted(set(roster) - set(wanted))))
    named = total = 0
    for geoid, rec in roster.items():
        names = [s["name"].lower() for s in rec.get("seats", []) if s.get("name")]
        twice = sorted({n for n in names if names.count(n) > 1})
        if twice:
            problems.append("%s names %s for more than one seat"
                            % (rec.get("name"), ", ".join(twice)))
        want = sum(SEATS.get(geoid, {}).values())
        if len(rec.get("seats", [])) != want:
            problems.append("%s carries %d seats, SEATS declares %d"
                            % (rec.get("name"), len(rec.get("seats", [])), want))
        for s in rec.get("seats", []):
            total += 1
            if s.get("name"):
                named += 1
                if not s.get("election") or not s.get("sourceUrl"):
                    problems.append("%s %s names somebody without the election "
                                    "that seated them" % (rec.get("name"), s.get("seat")))
            elif not s.get("unnamed"):
                problems.append("%s %s names nobody and says nothing about why"
                                % (rec.get("name"), s.get("seat")))
    if named < MIN_NAMED:
        problems.append("%d seats named, floor %d" % (named, MIN_NAMED))
    return problems, named, total


# Measured 2026-10-07: 249 of 268 seats named. The floor sits a little under
# it so a canvass that leaves a few more ranked-choice seats to later rounds
# does not stop the weekly refresh, while a parse that loses a city does.
MIN_NAMED = 240


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="offline: hold the shipped roster to SEATS and the city list")
    ap.add_argument("--cache", help="read saved <YYYYMMDD>.txt local results files "
                                    "from this folder instead of fetching")
    args = ap.parse_args()
    wanted = cities()
    if args.check:
        with open(OUT_FILE, encoding="utf-8") as fh:
            roster = json.load(fh)
        problems, named, total = check(roster, wanted)
        if problems:
            for p in problems:
                print("build-mn-city-councils: FAIL: " + p)
            raise SystemExit(1)
        print("build-mn-city-councils --check: OK — %d of %d seats named across "
              "%d cities, each dated to the election that seated it"
              % (named, total, len(roster)))
        return
    today = datetime.date.today()
    if args.cache:
        elections = read_cache(args.cache)
    else:
        import requests  # noqa: PLC0415
        elections = fetch_elections(requests.Session(), today)
    print("results files with local contests: %s"
          % ", ".join(d.isoformat() for d in sorted(elections)))
    found = contests(elections, wanted)
    roster = build(found, wanted, today)
    for rec in roster.values():
        for s in rec["seats"]:
            if not s.get("name"):
                print("  unnamed: %s %s — %s" % (rec["name"], s["seat"], s["unnamed"]))
    problems, named, total = check(roster, wanted)
    if problems:
        for p in problems:
            print("build-mn-city-councils: FAIL: " + p)
        raise SystemExit(1)
    with open(OUT_FILE, "w", encoding="utf-8") as fh:
        json.dump(roster, fh, indent=1, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    print("wrote %s: %d cities, %d of %d seats named"
          % (os.path.relpath(OUT_FILE, REPO), len(roster), named, total))


if __name__ == "__main__":
    main()
