#!/usr/bin/env python3
"""The elected board of every Minnesota school district, from the Secretary of
State's own election results, every name dated to the election that seated it.

WHAT THIS PUBLISHES AND WHAT IT DOES NOT. The Secretary of State publishes the
result of every school board contest it reports as a plain text file per
election day (`sdrace.txt`, under electionresultsfiles.sos.mn.gov/<YYYYMMDD>/),
the host `build_mn_city_councils.py` reads for city councils. A winner is a
fact with a date on it. It is NOT a statement of who sits on the board today:
a member who has resigned, and the person the board appointed in their place,
are in no results file. So every name carries its election, and the card says
so in words — the certified-returns posture the council roster ships under.

WHICH DISTRICT. The results name a district by its state number ("ISD #1",
"SSD #1"); the map's school-district cards are the Census's districts, keyed
by an NCES id. The join is the Minnesota Department of Education's own district
layer, which carries both the state number and the boundary: a Census district
joins to the department's district of the same name, and where the two spell
the name differently, to the one its interior point falls in. Both must give
one district, one to one. Measured 2026-10-07: 301 of the 330 Census districts
join by name, 28 more by interior point, and the one left is TIGER's "School
District Not Defined" filler. The single secondary district (Park Rapids for
grades 9-12 over Pine Point) is not joined: Pine Point's voters elect Pine
Point's board, not Park Rapids's, and a card naming Park Rapids's board there
would name people the reader does not vote for.

HOW BIG A BOARD IS. Nothing in the results says, so it is counted. A board
member serves four years and terms are staggered (Minn. Stat. 123B.09 subd. 1),
so the seats elected at a district's two most recent regular elections, two
years apart, are the whole board. Measured 2026-10-07 over the 2022-2025
files: of the 248 at-large boards with no special election to untangle, 110
come to six seats and 133 to seven, which is the statute's six plus its
optional seventh; the rest are boards that also elect by district.

WHICH SEAT A SPECIAL ELECTION FILLED is settled by the statute rather than
guessed: a vacancy is filled by a special election only when it occurs two
years or more before the term ends (123B.09 subd. 5b(b)), and the special is
held by the next November (subd. 5b(a)). So:
  * a special on the SAME DAY as a regular election filled a seat elected two
    years earlier — one of the older group, which the results cannot name;
  * a special in a year with no regular election may have filled a seat from
    either group still sitting, or one re-elected since, so the groups it could
    touch name nobody;
  * a special BEFORE the older of the two regular elections filled a seat that
    has been re-elected since, and is ignored.
Where a special takes one seat out of a group of four, the results cannot say
which of the four winners left, so those seats name nobody and say who the
candidates are.

SEATS WITH THEIR OWN NAME ("District 3", "Position 5", "Fairfax District") are
one seat each (or as many as the office elects at once), held by whoever won
the most recent contest for that office, regular or special.

FOUR WAYS A CONTEST IS NOT A WINNER, the council roster's: a primary (a general
carries a WRITE-IN line and a primary does not), a contest not yet
CANVASS_DAYS old, a seat won by write-in, and a tie at the last seat. No
Minnesota school board counts ranked ballots.

Usage:
    python3 mn/scripts/build_mn_school_boards.py          # fetch and write
    python3 mn/scripts/build_mn_school_boards.py --check  # offline gate
    python3 mn/scripts/build_mn_school_boards.py --cache DIR   # saved sdrace files
"""

import argparse
import datetime
import json
import os
import re
import sys
import time
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
REPO = os.path.dirname(INSTANCE)
FLEET_SCRIPTS = os.path.join(REPO, "scripts")
if FLEET_SCRIPTS not in sys.path:
    sys.path.insert(0, FLEET_SCRIPTS)

FILES_HOST = "https://electionresultsfiles.sos.mn.gov"
RESULTS_FILE = FILES_HOST + "/%s/sdrace.txt"
MDE_LAYER = ("https://enterprise.gisdata.mn.gov/aghost/rest/services/"
             "us_mn_state_mde/bdry_school_district_boundaries/FeatureServer/0/query")
TIGER_LAYER = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
               "School/MapServer/%d/query")
# Census layers whose districts elect their own board: 0 unified, 2 elementary.
# Layer 1 (secondary) is deliberately left out; see the docstring.
TIGER_LAYERS = (0, 2)
USER_AGENT = "districtry/1.0 (+https://districtry.com/mn/)"
REQUEST_TIMEOUT = 120
PACE_SECONDS = 0.5
FIRST_ELECTION = datetime.date(2022, 11, 8)
CANVASS_DAYS = 21
OUT_FILE = os.path.join(INSTANCE, "data", "app", "mn-school-boards.json")
STATE_FIPS = "27"

# MDE's two-digit district type, as the results file abbreviates it.
DISTRICT_TYPE = {"01": "ISD", "02": "CSD", "03": "SSD"}

OFFICE_RE = re.compile(
    r"^(?P<special>Special Election for )?School Board Member "
    r"(?:(?P<seat>District \d+|Position \d+|[A-Z][A-Za-z.' -]* District|at Large|At Large) )?"
    r"\((?P<type>ISD|SSD|CSD) #(?P<num>\d+)\)(?: \(Elect (?P<elect>\d+)\))?$")

# Name words that say what kind of body a district is rather than which one,
# dropped before two spellings of one district's name are compared.
NAME_NOISE = {"public", "school", "schools", "district", "area", "community",
              "the", "of", "isd", "independent", "special", "saint", "st"}

# Measured 2026-10-07 (see the docstring); the floors sit under it so a
# canvass that leaves a few more seats unnamed does not stop the weekly
# refresh, while a parse that loses a file or a join does.
MIN_DISTRICTS = 310
MIN_NAMED = 1600


def fail(msg):
    raise SystemExit("build-mn-school-boards: FATAL: %s" % msg)


def get_json(session, url, params):
    resp = session.get(url, params=params, headers={"User-Agent": USER_AGENT},
                       timeout=REQUEST_TIMEOUT)
    if resp.status_code != 200:
        fail("%s answered HTTP %d" % (url, resp.status_code))
    data = resp.json()
    if isinstance(data, dict) and data.get("error"):
        # an ArcGIS error object is a failure, never an empty answer
        fail("%s answered an error: %r" % (url, data["error"]))
    return data


def norm_name(name):
    words = re.sub(r"[^a-z0-9]+", " ", name.lower().replace("-", " ")).split()
    return " ".join(w for w in words if w not in NAME_NOISE)


def point_in_ring(x, y, ring):
    inside = False
    for i in range(len(ring)):
        x1, y1 = ring[i]
        x2, y2 = ring[i - 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def point_in_geometry(x, y, geom):
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    return any(sum(point_in_ring(x, y, r) for r in p) % 2 == 1 for p in polys)


def fetch_join(session):
    """{census GEOID: {"key": "ISD 1", "name": census name, "website": url or
    None, "joinedBy": "name"|"point"}} for every Census district that elects a
    board, joined one to one to the Department of Education's districts."""
    from scraper_common import require_robots_once  # noqa: PLC0415
    require_robots_once(MDE_LAYER, USER_AGENT)
    require_robots_once(TIGER_LAYER % 0, USER_AGENT)
    mde = get_json(session, MDE_LAYER, {
        "where": "1=1", "outFields": "sdtype,sdnumber,prefname,web_url",
        "outSR": "4326", "maxAllowableOffset": "0.0005",
        "geometryPrecision": "5", "f": "geojson"})["features"]
    if len(mde) < 320:
        fail("the Department of Education's layer returned %d districts" % len(mde))
    depts = []
    for f in mde:
        p = f["properties"]
        kind = DISTRICT_TYPE.get(p.get("sdtype"))
        if kind is None:
            fail("unknown district type %r for %r" % (p.get("sdtype"), p.get("prefname")))
        url = (p.get("web_url") or "").strip()
        depts.append({"key": "%s %d" % (kind, int(p["sdnumber"])),
                      "name": p["prefname"], "norm": norm_name(p["prefname"]),
                      "website": url if url.startswith("http") else None,
                      "geometry": f.get("geometry")})
    by_norm = {}
    for d in depts:
        by_norm.setdefault(d["norm"], []).append(d)
    out = {}
    for layer in TIGER_LAYERS:
        time.sleep(PACE_SECONDS)
        feats = get_json(session, TIGER_LAYER % layer, {
            "where": "STATE='%s'" % STATE_FIPS,
            "outFields": "GEOID,NAME,INTPTLAT,INTPTLON",
            "returnGeometry": "false", "f": "json"})["features"]
        for f in feats:
            a = f["attributes"]
            if a["NAME"] == "School District Not Defined":
                continue
            named = by_norm.get(norm_name(a["NAME"]), [])
            if len(named) == 1:
                hit, how = named[0], "name"
            else:
                x, y = float(a["INTPTLON"]), float(a["INTPTLAT"])
                inside = [d for d in depts
                          if d["geometry"] and point_in_geometry(x, y, d["geometry"])]
                if len(inside) != 1:
                    fail("%s (%s) joins to %d Department of Education districts"
                         % (a["NAME"], a["GEOID"], len(inside)))
                hit, how = inside[0], "point"
            out[a["GEOID"]] = {"key": hit["key"], "name": a["NAME"],
                               "website": hit["website"], "joinedBy": how}
    keys = [v["key"] for v in out.values()]
    twice = sorted({k for k in keys if keys.count(k) > 1})
    if twice:
        fail("two Census districts join to one Department of Education "
             "district: %s" % ", ".join(twice))
    return out


def fetch_elections(session, today):
    """{date: text} for every Tuesday since FIRST_ELECTION whose results
    directory carries a school board file."""
    from scraper_common import require_robots_once  # noqa: PLC0415
    require_robots_once(RESULTS_FILE % FIRST_ELECTION.strftime("%Y%m%d"), USER_AGENT)
    out = {}
    day = FIRST_ELECTION
    while day <= today:
        url = RESULTS_FILE % day.strftime("%Y%m%d")
        resp = session.get(url, headers={"User-Agent": USER_AGENT},
                           timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            if resp.content.strip():
                out[day] = resp.content.decode("latin-1")
        elif resp.status_code != 404:
            fail("%s answered HTTP %d — a probe that cannot tell an empty day "
                 "from a failure must stop" % (url, resp.status_code))
        time.sleep(PACE_SECONDS)
        day += datetime.timedelta(days=7)
    if FIRST_ELECTION not in out:
        fail("the 2022 general's school board results file is missing")
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


def contests(elections):
    """Every school board contest, oldest first, keyed by district."""
    found = {}
    for day in sorted(elections):
        groups = {}
        for line in elections[day].splitlines():
            if not line.strip():
                continue
            f = line.split(";")
            if len(f) < 16:
                fail("%s: a line with %d fields: %r" % (day, len(f), line[:120]))
            office = f[4].strip()
            m = OFFICE_RE.match(office)
            if not m:
                fail("%s: an office this parser does not read: %r — a new "
                     "office form; read it and extend OFFICE_RE" % (day, office))
            groups.setdefault(office, (m, []))[1].append(f)
        for office, (m, rows) in sorted(groups.items()):
            seat = m.group("seat") or "At Large"
            if seat.lower() == "at large":
                seat = "At Large"
            key = "%s %d" % (m.group("type"), int(m.group("num")))
            found.setdefault(key, []).append({
                "date": day, "office": office, "seat": seat,
                "special": bool(m.group("special")),
                "elect": int(m.group("elect") or 1),
                "candidates": [(r[7].strip(), int(r[13])) for r in rows],
            })
    return found


def is_general(c):
    return any(n.upper() == "WRITE-IN" for n, _ in c["candidates"])


def winners(c):
    """[(name or None, why)] for each seat this contest filled."""
    k = c["elect"]
    cands = sorted(c["candidates"], key=lambda x: -x[1])
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


def term_over(c, today):
    """The first of January by which this election's term has certainly
    ended. A regular term is four years from the January after the election
    (123B.09 subd. 1). A special filled the rest of a term elected at most two
    years before it, so it ends no later than one year sooner."""
    years = 4 if c["special"] else 5
    end = datetime.date(c["date"].year + years, 1, 1)
    return end if today >= end else None


def seat_rec(c, seat, name, why, today=None):
    rec = {"seat": seat, "election": c["date"].isoformat(),
           "sourceUrl": RESULTS_FILE % c["date"].strftime("%Y%m%d")}
    if c["special"]:
        rec["special"] = True
    ended = term_over(c, today) if today else None
    if name and ended:
        name, why = None, ("%s won this seat on %s and its term ended by %s; no "
                           "later result names who holds it"
                           % (name, c["date"].isoformat(), ended.isoformat()))
    if name:
        rec["name"] = name
    else:
        rec["unnamed"] = why
    return rec


def pool_seats(events, today, label="At Large"):
    """The seats under one office name, staggered: the two newest regular
    elections two years apart, with the special elections the statute places
    among them. Returns (seats, partial-or-None)."""
    gens = [c for c in events if is_general(c)]
    held = [c for c in gens if (today - c["date"]).days < CANVASS_DAYS]
    gens = [c for c in gens if c not in held]
    out = []
    for c in held:
        out.append({"seat": label, "unnamed": "the %s election is not yet "
                    "canvassed" % c["date"].isoformat()})
    regular = sorted((c for c in gens if not c["special"]),
                     key=lambda c: c["date"], reverse=True)
    if not regular:
        return out, None
    newest = regular[0]
    older = None
    for c in regular[1:]:
        if (newest["date"] - c["date"]).days in range(700, 760):
            older = c
            break
    partial = None
    if older is None:
        partial = ("the results carry one regular election for this board's "
                   "%s seats since %s, so the seats elected two years "
                   "before it are not shown"
                   % ("at-large" if label == "At Large" else label,
                      FIRST_ELECTION.isoformat()))
    floor = older["date"] if older else newest["date"]
    current, between = [], []
    for c in sorted((c for c in gens if c["special"]), key=lambda c: c["date"]):
        if c["date"] >= newest["date"]:
            # on the newest regular's day it filled a seat elected two years
            # before; after it, a seat from either group — current either way
            current.append(c)
        elif c["date"] > floor:
            # a year between the two: a seat from the older group, or one
            # re-elected at the newest regular since (subd. 5b(a)-(b))
            between.append(c)
    new_sure = not any(c["date"] > newest["date"] for c in current)
    groups = [newest] + ([older] if older else [])
    size = sum(c["elect"] for c in groups)
    seats = []
    for c in current:
        for n, w in winners(c):
            seats.append(seat_rec(c, label, n, w, today))
    doubt, why = [], []
    for c in groups:
        sure = (c is newest and new_sure) or (c is older and not current and not between)
        if c is older and older is not None and partial is None and not current and not between:
            sure = True
        if sure:
            seats.extend(seat_rec(c, label, n, w, today) for n, w in winners(c))
        else:
            doubt.append(c)
    if doubt:
        dates = sorted({c["date"].isoformat() for c in current + between})
        why.append("a special election on %s filled a seat on this board, and "
                   "the results do not say whose seat it was (Minn. Stat. "
                   "123B.09 subd. 5b)" % " and ".join(dates))
        names = []
        for c in doubt + between:
            got = [n for n, _ in winners(c) if n]
            if got:
                names.append("on %s %s" % (c["date"].isoformat(), ", ".join(got)))
        said = "%s. Elected %s" % (why[0][0].upper() + why[0][1:], "; ".join(names))
        for _ in range(max(0, size - len(seats))):
            seats.append({"seat": label, "election": doubt[-1]["date"].isoformat(),
                          "sourceUrl": RESULTS_FILE % doubt[-1]["date"].strftime("%Y%m%d"),
                          "unnamed": said})
    return out + seats, partial


def named_seat(seat, events, today):
    """A seat with its own name: whoever won its most recent contest."""
    gens = [c for c in events if is_general(c)]
    held = [c for c in gens if (today - c["date"]).days < CANVASS_DAYS]
    gens = [c for c in gens if c not in held]
    if held:
        return [{"seat": seat, "unnamed": "the %s election is not yet canvassed"
                 % held[-1]["date"].isoformat()}] * held[-1]["elect"]
    if not gens:
        return []
    regular = sorted({c["date"] for c in gens if not c["special"]})
    if any((b - a).days in range(700, 760) for a in regular for b in regular):
        # elected in both halves of the cycle: two staggered seats under one
        # name (GFW's three town districts, measured 2026-10-07)
        return pool_seats(events, today, seat)[0]
    last = max(gens, key=lambda c: (c["date"], c["special"]))
    return [seat_rec(last, seat, n, w, today) for n, w in winners(last)]


def vacate_moved(seats):
    """A person who won a seat and later won a different seat on the same
    board has left the first one."""
    named = [x for x in seats if x.get("name")]
    left = []
    for rec in named:
        later = [x for x in named if x is not rec
                 and x["name"].lower() == rec["name"].lower()
                 and x["election"] > rec["election"]]
        if later:
            left.append((rec, max(later, key=lambda x: x["election"])))
    for rec, moved in left:
        rec["unnamed"] = ("%s, who won this seat on %s, won another seat on "
                          "this board on %s, and the results do not say who "
                          "holds this one now"
                          % (rec.pop("name"), rec["election"], moved["election"]))
    # the same person winning the same election twice (one seat counted in
    # two offices) keeps one record
    seen = set()
    for rec in seats:
        if rec.get("name"):
            k = (rec["name"].lower(), rec["election"])
            if k in seen:
                rec["unnamed"] = "%s appears twice in the %s results" % (
                    rec.pop("name"), rec["election"])
            seen.add(k)


def build(found, join, today):
    by_key = {v["key"]: g for g, v in join.items()}
    unknown = sorted(set(found) - set(by_key))
    roster = {}
    for key, events in sorted(found.items()):
        geoid = by_key.get(key)
        if geoid is None:
            continue
        offices = {}
        for c in events:
            offices.setdefault(c["seat"], []).append(c)
        seats, partial = [], None
        for seat in sorted(offices, key=lambda s: (s == "At Large", s)):
            if seat == "At Large":
                got, partial = pool_seats(offices[seat], today)
            else:
                got = named_seat(seat, offices[seat], today)
            seats.extend(got)
        vacate_moved(seats)
        rec = {"name": join[geoid]["name"], "district": key, "seats": seats}
        if join[geoid]["website"]:
            rec["website"] = join[geoid]["website"]
        if partial:
            rec["partial"] = partial
        roster[geoid] = rec
    return roster, unknown


def check(roster):
    problems = []
    named = total = 0
    for geoid, rec in roster.items():
        if not re.match(r"^%s\d{5}$" % STATE_FIPS, geoid):
            problems.append("%r is not a Minnesota Census school district id" % geoid)
        if not re.match(r"^(ISD|SSD|CSD) \d+$", rec.get("district", "")):
            problems.append("%s carries no state district number" % geoid)
        names = [s["name"].lower() for s in rec.get("seats", []) if s.get("name")]
        twice = sorted({n for n in names if names.count(n) > 1})
        if twice:
            problems.append("%s names %s for more than one seat"
                            % (rec.get("name"), ", ".join(twice)))
        if not rec.get("seats"):
            problems.append("%s carries no seats" % rec.get("name"))
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
    if len(roster) < MIN_DISTRICTS:
        problems.append("%d districts, floor %d" % (len(roster), MIN_DISTRICTS))
    if named < MIN_NAMED:
        problems.append("%d seats named, floor %d" % (named, MIN_NAMED))
    return problems, named, total


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="offline: hold the shipped roster to its own rules")
    ap.add_argument("--cache", help="read saved <YYYYMMDD>.txt sdrace files from "
                                    "this folder instead of fetching them")
    ap.add_argument("--join-cache", help="read a saved join JSON instead of "
                                         "fetching the two district layers")
    args = ap.parse_args()
    if args.check:
        with open(OUT_FILE, encoding="utf-8") as fh:
            roster = json.load(fh)
        problems, named, total = check(roster)
        if problems:
            for p in problems:
                print("build-mn-school-boards: FAIL: " + p)
            raise SystemExit(1)
        print("build-mn-school-boards --check: OK — %d of %d seats named across "
              "%d districts, each dated to the election that seated it"
              % (named, total, len(roster)))
        return
    today = datetime.date.today()
    import requests  # noqa: PLC0415
    session = requests.Session()
    if args.join_cache:
        with open(args.join_cache, encoding="utf-8") as fh:
            join = json.load(fh)
    else:
        join = fetch_join(session)
    how = [v["joinedBy"] for v in join.values()]
    print("joined %d Census districts: %d by name, %d by interior point"
          % (len(join), how.count("name"), how.count("point")))
    elections = read_cache(args.cache) if args.cache else fetch_elections(session, today)
    print("results files with school board contests: %s"
          % ", ".join(d.isoformat() for d in sorted(elections)))
    found = contests(elections)
    roster, unknown = build(found, join, today)
    if unknown:
        print("in the results and on no Census district (not published): %s"
              % ", ".join(unknown))
    for rec in roster.values():
        if rec.get("partial"):
            print("  partial: %s — %s" % (rec["name"], rec["partial"]))
    problems, named, total = check(roster)
    if problems:
        for p in problems:
            print("build-mn-school-boards: FAIL: " + p)
        raise SystemExit(1)
    with open(OUT_FILE, "w", encoding="utf-8") as fh:
        json.dump(roster, fh, indent=1, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    print("wrote %s: %d districts, %d of %d seats named"
          % (os.path.relpath(OUT_FILE, REPO), len(roster), named, total))


if __name__ == "__main__":
    main()
