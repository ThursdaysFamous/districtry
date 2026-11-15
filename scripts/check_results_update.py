#!/usr/bin/env python3
"""
May a rebuilt election results file go live with no person looking at it?

WHY THIS EXISTS (2026-11-15). Every results refresh on this site opens a pull
request that waits for a look before it is merged. Adam chose otherwise for one
night ("Nightly", 2026-11-15): on the night of Chicago's election of 23
February 2027 the count is read three times and once more the next morning,
and each update goes live once the automated checks pass. Those checks ask
whether the app still works. None of them asks whether the NUMBERS look like a
count in progress, which is the question a reviewer answers, so this script
asks it, of the rebuilt file against the one the site ships
(.github/workflows/update-chicago-city-election-results.yml).

A count in progress only grows. So an update is HELD for a look, and the site
keeps the last file that passed, when the rebuilt file

  - is for another election than the shipped one, or says certified where the
    shipped one did not (a certification always gets a look);
  - has lost a race, a choice in a race, or a precinct the shipped one had, or
    gained a race (a choice may be added: the Board lists a write-in candidate
    once votes for one are tallied);
  - has fewer votes than the shipped one anywhere they can be compared: a
    race's total, a choice's total, the ballots cast, a precinct's ballots, a
    choice's votes in a precinct, or a precinct that held votes holding none;
  - does not have the number of races of each kind that `--expect` names.
    The first update of a night has no earlier count to compare with, so this
    is what stands in for one: Chicago's city election is 3 citywide offices,
    50 wards and 22 police district councils, and a results page missing some
    of them is one the Board is still building.

There is NOTHING to publish when no vote has been counted (the Board lists an
election's races before its first count) and nothing held votes before, or
when only the reading time moved. Otherwise the verdict is PUBLISH.

WHAT IT CANNOT SEE. A count that is wrong and larger passes: this compares a
file with the one before it, never with the truth. The builder has already
held the Board's rows to each other (each ward's precincts sum to the ward's
total row, and the wards to the citywide row), and nothing here repeats that.
A candidate left off the Board's page from its first count is not missed,
because there is no earlier file that names them.

AND WHEN. The choice was for the night and the morning after, not for every
day until the count is certified, so `--phase` answers where a moment falls
for the shipped file's election: `before` the polls close on election day
(7 pm in the election's own time zone, when there is no count to read),
`night` from then until noon the next day, and `after`. The job publishes by
itself only in `night`; before it the job reads nothing, and after it every
update waits for a look, as each day's did after November's election.

    python3 scripts/check_results_update.py --name chicago-election-results \\
        --expect city=3 --expect city-council=50 --expect police-council=22
    python3 scripts/check_results_update.py --name chicago-election-results --phase
    python3 scripts/check_results_update.py --selftest

Prints each reason and then `verdict: publish|nothing|hold`, and writes
`verdict=` to $GITHUB_OUTPUT when that is set. It exits 0 on all three: the
verdict is the answer, and a non-zero exit means the question could not be
asked (a file that cannot be read).
"""

import argparse
import copy
import datetime
import json
import os
import re
import subprocess
import sys
import zoneinfo

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_REASONS = 12
POLLS_CLOSE = 19    # 7 pm on election day (10 ILCS 5/17-1), in the election's zone
NIGHT_ENDS = 12     # noon the next day


def phase(election_date, now, tz):
    """"before", "night" or "after" for the aware datetime `now` against an
    election held on `election_date` (ISO) in the zone `tz`."""
    zone = zoneinfo.ZoneInfo(tz)
    day = datetime.date.fromisoformat(election_date)
    closes = datetime.datetime.combine(day, datetime.time(POLLS_CLOSE), zone)
    ends = datetime.datetime.combine(day + datetime.timedelta(days=1),
                                     datetime.time(NIGHT_ENDS), zone)
    if now < closes:
        return "before"
    return "night" if now < ends else "after"


def num(n):
    return "{:,}".format(n) if isinstance(n, int) else str(n)


def without_read(idx):
    """An index or part file with its reading times taken out: every read
    stamps them, so two reads of one count differ only there."""
    d = copy.deepcopy(idx)
    d.pop("read", None)
    for s in d.get("sources") or []:
        s.pop("read", None)
    return d


def holds_votes(idx):
    t = ((idx.get("turnout") or {}).get("total") or [None, None])
    return bool(t[1]) or any((c.get("total") or [0])[0] for c in idx.get("contests") or [])


def precinct_holds(p):
    """A precinct that holds a ballot or a vote in some race (the writer's
    `reported`, read from the part file so a finished count needs no string)."""
    t = (p or {}).get("turnout") or [None, None]
    return bool(t[1]) or any(any(row[1:]) for row in (p or {}).get("contests") or [])


def judge(old, new, old_parts, new_parts, expect):
    """(verdict, [reason]) for a rebuilt index `new` against the shipped `old`.
    `old_parts` and `new_parts` are {precinct key: {turnout, contests}} over
    every part file; `expect` is {group id: number of races}."""
    if old is None:
        return "hold", ["No results file is shipped to compare the rebuilt one with."]
    if (old.get("electionDate"), old.get("election")) != (new.get("electionDate"), new.get("election")):
        return "hold", ["The rebuilt file is for the %s of %s. The shipped file is for the %s of %s."
                        % (new.get("election"), new.get("electionDate"),
                           old.get("election"), old.get("electionDate"))]
    old_races, new_races = old.get("contests") or [], new.get("contests") or []
    if not new_races:
        if old_races:
            return "hold", ["The rebuilt file has no races. The shipped file has %s."
                            % num(len(old_races))]
        return "nothing", ["No count has been published for this election yet."]
    if not holds_votes(new):
        if holds_votes(old):
            return "hold", ["The rebuilt file holds no votes. The shipped file does."]
        return "nothing", ["The races are listed and no vote has been counted yet."]
    if without_read(old) == without_read(new) and old_parts == new_parts:
        return "nothing", ["Nothing changed since the shipped file but the time it was read."]

    reasons = []
    more = [0]

    def hold(text):
        if len(reasons) < MAX_REASONS:
            reasons.append(text)
        else:
            more[0] += 1

    if new.get("certified") and not old.get("certified"):
        hold("The rebuilt file says the results are certified. A certification is looked at "
             "before it is published.")
    for group, want in sorted(expect.items()):
        got = sum(1 for c in new_races if c.get("group") == group)
        if got != want:
            hold("The rebuilt file has %s race(s) of the kind '%s'. This election has %s."
                 % (num(got), group, num(want)))

    if old_races:
        if old.get("precincts") != new.get("precincts"):
            hold("The list of precincts changed (%s shipped, %s rebuilt)."
                 % (num(len(old.get("precincts") or [])), num(len(new.get("precincts") or []))))
        new_by = {c["id"]: c for c in new_races}
        old_ids = set(c["id"] for c in old_races)
        gained = [c["name"] for c in new_races if c["id"] not in old_ids]
        if gained:
            hold("%s race(s) are in the rebuilt file and not in the shipped one: %s."
                 % (num(len(gained)), "; ".join(gained[:4]) + ("; …" if len(gained) > 4 else "")))
        maps = {}       # contest id -> [(old position, new position, choice)]
        for c in old_races:
            n = new_by.get(c["id"])
            if n is None or n["name"] != c["name"]:
                hold("The race '%s' is no longer in the results." % c["name"])
                continue
            where = {name: i for i, name in enumerate(n["choices"])}
            pairs = []
            for i, name in enumerate(c["choices"]):
                if name not in where:
                    hold("%s is no longer listed in the race '%s'." % (name, c["name"]))
                    continue
                pairs.append((i, where[name], name))
                was, now = c["total"][1 + i] or 0, n["total"][1 + where[name]] or 0
                if now < was:
                    hold("%s's votes in '%s' went down, from %s to %s."
                         % (name, c["name"], num(was), num(now)))
            maps[c["id"]] = (c["name"], pairs)
            if (n["total"][0] or 0) < (c["total"][0] or 0):
                hold("The votes counted in '%s' went down, from %s to %s."
                     % (c["name"], num(c["total"][0]), num(n["total"][0])))
        was = ((old.get("turnout") or {}).get("total") or [None, None])[1] or 0
        now = ((new.get("turnout") or {}).get("total") or [None, None])[1] or 0
        if now < was:
            hold("The ballots cast went down, from %s to %s." % (num(was), num(now)))

        emptied, fewer_ballots, fewer_votes = [], [], []
        for key in old.get("precincts") or []:
            a, b = old_parts.get(key), new_parts.get(key)
            if a is None:
                continue
            if b is None:
                emptied.append(key)
                continue
            if precinct_holds(a) and not precinct_holds(b):
                emptied.append(key)
                continue
            ta, tb = (a.get("turnout") or [None, None])[1] or 0, (b.get("turnout") or [None, None])[1] or 0
            if tb < ta:
                fewer_ballots.append("%s (%s to %s)" % (key, num(ta), num(tb)))
            rows = {row[0]: row for row in b.get("contests") or []}
            for row in a.get("contests") or []:
                if row[0] not in maps:
                    continue
                name, pairs = maps[row[0]]
                other = rows.get(row[0])
                if other is None:
                    fewer_votes.append("%s, %s (the race is gone from the precinct)" % (key, name))
                    continue
                for i, j, choice in pairs:
                    if (other[2 + j] or 0) < (row[2 + i] or 0):
                        fewer_votes.append("%s, %s, %s (%s to %s)"
                                           % (key, name, choice, num(row[2 + i]), num(other[2 + j])))
        if emptied:
            hold("%s precinct(s) that held votes hold none now (the first: %s)."
                 % (num(len(emptied)), emptied[0]))
        if fewer_ballots:
            hold("The ballots cast went down in %s precinct(s) (the first: %s)."
                 % (num(len(fewer_ballots)), fewer_ballots[0]))
        if fewer_votes:
            hold("A choice's votes went down in %s precinct count(s) (the first: %s)."
                 % (num(len(fewer_votes)), fewer_votes[0]))

    if more[0]:
        reasons.append("And %s more of the same kinds." % num(more[0]))
    if reasons:
        return "hold", reasons
    now = ((new.get("turnout") or {}).get("total") or [None, None])[1]
    return "publish", [
        "%s race(s), %s ballots cast%s." % (
            num(len(new_races)), num(now) if now is not None else "no count of",
            "" if old_races else "; the first count published for this election")]


# ---------------------------------------------------------------- reading

def parts_of(docs):
    out = {}
    for d in docs:
        out.update(d.get("precincts") or {})
    return out


def read_new(app_data, name):
    with open(os.path.join(REPO_ROOT, app_data, name + ".json"), encoding="utf-8") as f:
        idx = json.load(f)
    d = os.path.join(REPO_ROOT, app_data, name)
    docs = []
    if os.path.isdir(d):
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".json"):
                with open(os.path.join(d, fn), encoding="utf-8") as f:
                    docs.append(json.load(f))
    return idx, parts_of(docs)


def git_show(base, path):
    r = subprocess.run(["git", "show", "%s:%s" % (base, path)], cwd=REPO_ROOT,
                       capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def read_old(app_data, name, base):
    text = git_show(base, "%s/%s.json" % (app_data, name))
    if text is None:
        return None, {}
    r = subprocess.run(["git", "ls-tree", "--name-only", base, "%s/%s/" % (app_data, name)],
                       cwd=REPO_ROOT, capture_output=True, text=True)
    docs = []
    for path in r.stdout.split():
        if path.endswith(".json"):
            body = git_show(base, path)
            if body is None:
                raise SystemExit("check-results-update: cannot read %s at %s" % (path, base))
            docs.append(json.loads(body))
    return json.loads(text), parts_of(docs)


# ---------------------------------------------------------------- selftest

def _fixture():
    """A two-precinct election with two races, part counted."""
    idx = {
        "election": "Municipal General Election", "electionDate": "2099-02-23",
        "read": "2099-02-24T02:10:00Z", "certified": False,
        "sources": [{"id": "chicago", "read": "2099-02-24T02:10:00Z"}],
        "turnout": {"columns": ["registered", "ballots"], "total": [900, 300]},
        "precincts": ["01001", "01002"], "parts": ["ward-01", "ward-01"],
        "contests": [
            {"id": "11", "name": "Mayor", "group": "city", "choices": ["A", "B"],
             "total": [290, 190, 100]},
            {"id": "14", "name": "Alderperson 1st Ward", "group": "city-council",
             "choices": ["C", "D"], "total": [280, 80, 200]},
        ],
    }
    parts = {
        "01001": {"turnout": [500, 300], "contests": [["11", 290, 190, 100], ["14", 280, 80, 200]]},
        "01002": {"turnout": [400, 0], "contests": [["11", 0, 0, 0], ["14", 0, 0, 0]]},
    }
    return idx, parts


def selftest():
    expect = {"city": 1, "city-council": 1}
    old, old_parts = _fixture()
    empty = {"election": old["election"], "electionDate": old["electionDate"], "read": None,
             "certified": False, "sources": [], "turnout": {"total": [None, None]},
             "precincts": [], "parts": [], "contests": []}
    cases = []

    def case(want, why, o, n, op, np, exp=expect, says=None):
        got, reasons = judge(o, n, op, np, exp)
        ok = got == want and (says is None or any(says in r for r in reasons))
        cases.append((ok, "%s: wanted %s%s, got %s %r" % (
            why, want, " saying %r" % says if says else "", got, reasons)))

    def grown():
        n, p = _fixture()
        n["read"] = "2099-02-24T04:10:00Z"
        n["sources"][0]["read"] = n["read"]
        n["turnout"]["total"] = [900, 520]
        n["contests"][0]["total"] = [505, 300, 205]
        n["contests"][1]["total"] = [490, 150, 340]
        p["01002"] = {"turnout": [400, 220], "contests": [["11", 215, 110, 105], ["14", 210, 70, 140]]}
        return n, p

    # nothing to publish
    n, p = _fixture()
    n["read"] = "2099-02-24T03:00:00Z"
    n["sources"][0]["read"] = n["read"]
    case("nothing", "only the reading time moved", old, n, old_parts, p)
    case("nothing", "the stand-in file again", empty, copy.deepcopy(empty), {}, {})
    n, p = _fixture()
    n["turnout"]["total"] = [900, 0]
    for c in n["contests"]:
        c["total"] = [0, 0, 0]
    for k in p:
        p[k] = {"turnout": [p[k]["turnout"][0], 0], "contests": [["11", 0, 0, 0], ["14", 0, 0, 0]]}
    case("nothing", "the races listed with no vote yet", empty, n, {}, p)
    case("hold", "votes gone back to none", old, n, old_parts, p, says="holds no votes")

    # publish
    n, p = _fixture()
    case("publish", "the first count of a night", empty, n, {}, p, says="first count")
    n, p = grown()
    case("publish", "a count further along", old, n, old_parts, p)
    n, p = grown()
    n["contests"][0]["choices"] = ["A", "W (WRITE-IN)", "B"]
    n["contests"][0]["total"] = [506, 300, 1, 205]
    p["01001"]["contests"][0] = ["11", 290, 190, 0, 100]
    p["01002"]["contests"][0] = ["11", 216, 110, 1, 105]
    case("publish", "a write-in added in the middle of a race's choices", old, n, old_parts, p)

    # hold
    n, p = _fixture()
    case("hold", "the first count missing a kind of race", empty, n, {}, p,
         exp={"city": 1, "city-council": 2}, says="'city-council'")
    n, p = grown()
    n["electionDate"] = "2099-04-06"
    case("hold", "another election's file", old, n, old_parts, p, says="is for the")
    n, p = grown()
    n["certified"] = True
    case("hold", "a certification", old, n, old_parts, p, says="certified")
    n, p = grown()
    n["contests"][0]["total"] = [505, 180, 325]
    case("hold", "a candidate's total going down", old, n, old_parts, p, says="A's votes in 'Mayor'")
    n, p = grown()
    n["contests"][0]["choices"] = ["A", "Z"]
    case("hold", "a candidate no longer listed", old, n, old_parts, p, says="B is no longer listed")
    n, p = grown()
    del n["contests"][1]
    case("hold", "a race gone", old, n, old_parts, p, says="no longer in the results",
         exp={"city": 1})
    n, p = grown()
    n["contests"].append({"id": "99", "name": "Question", "group": "questions",
                          "choices": ["Yes", "No"], "total": [5, 3, 2]})
    case("hold", "a race appearing", old, n, old_parts, p, says="not in the shipped one")
    n, p = grown()
    n["turnout"]["total"] = [900, 250]
    case("hold", "ballots cast going down", old, n, old_parts, p, says="ballots cast went down")
    n, p = grown()
    p["01001"] = {"turnout": [500, 0], "contests": [["11", 0, 0, 0], ["14", 0, 0, 0]]}
    case("hold", "a counted precinct emptied", old, n, old_parts, p, says="hold none now")
    n, p = grown()
    p["01001"]["contests"][0] = ["11", 290, 185, 105]
    case("hold", "a candidate's votes down in one precinct while the totals rise",
         old, n, old_parts, p, says="01001, Mayor, A (190 to 185)")
    n, p = grown()
    p["01001"]["turnout"] = [500, 280]
    case("hold", "a precinct's ballots down", old, n, old_parts, p, says="01001 (300 to 280)")
    n, p = grown()
    n["precincts"] = ["01001"]
    case("hold", "a precinct dropped from the list", old, n, old_parts, p, says="list of precincts")
    n, p = grown()
    n["contests"] = []
    case("hold", "every race gone", old, n, old_parts, p, says="has no races")
    case("hold", "no shipped file", None, n, {}, p, says="No results file")
    # many reasons are capped, with the rest counted
    n, p = grown()
    n["contests"] = [dict(c, name=c["name"] + " x") for c in n["contests"]] + [
        {"id": str(100 + i), "name": "Q%d" % i, "group": "questions", "choices": ["Y"],
         "total": [1, 1]} for i in range(3)]
    o2 = copy.deepcopy(old)
    o2["contests"] += [{"id": str(200 + i), "name": "Gone %d" % i, "group": "city",
                        "choices": ["Y"], "total": [1, 1]} for i in range(MAX_REASONS + 3)]
    got, reasons = judge(o2, n, old_parts, p, {})
    cases.append((got == "hold" and len(reasons) == MAX_REASONS + 1 and "more" in reasons[-1],
                  "a long list of reasons is cut at %d and says how many more: %r"
                  % (MAX_REASONS, reasons[-1:])))

    # the night: Chicago is six hours behind UTC in February, five in April
    utc = datetime.timezone.utc
    for when, want in (((2027, 2, 23, 18, 0), "before"),      # noon on election day
                       ((2027, 2, 24, 0, 59), "before"),      # 6:59 pm
                       ((2027, 2, 24, 1, 0), "night"),        # 7 pm: the polls close
                       ((2027, 2, 24, 6, 0), "night"),        # midnight
                       ((2027, 2, 24, 13, 0), "night"),       # 7 am the next morning
                       ((2027, 2, 24, 17, 59), "night"),      # 11:59 am
                       ((2027, 2, 24, 18, 0), "after"),       # noon
                       ((2027, 3, 1, 12, 0), "after")):
        got = phase("2027-02-23", datetime.datetime(*when, tzinfo=utc), "America/Chicago")
        cases.append((got == want, "%r UTC is %s for an election on 2027-02-23, got %s"
                      % (when, want, got)))
    got = phase("2027-04-06", datetime.datetime(2027, 4, 7, 0, 0, tzinfo=utc), "America/Chicago")
    cases.append((got == "night", "7 pm in daylight time is midnight UTC, got %s" % got))
    got = phase("2027-04-06", datetime.datetime(2027, 4, 6, 23, 59, tzinfo=utc), "America/Chicago")
    cases.append((got == "before", "6:59 pm in daylight time, got %s" % got))

    bad = [why for ok, why in cases if not ok]
    for why in bad:
        print("check-results-update: selftest FAIL — " + why, file=sys.stderr)
    if bad:
        raise SystemExit(1)
    print("check-results-update: selftest OK — %d cases: nothing to publish, a count further "
          "along, each thing a count in progress does not do, and where a night starts and "
          "ends" % len(cases))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--name", help="the results files' base name (data/app/<name>.json)")
    ap.add_argument("--app-data", default="il/data/app")
    ap.add_argument("--base", default="HEAD", help="the commit holding the shipped file")
    ap.add_argument("--expect", action="append", default=[], metavar="GROUP=N",
                    help="the number of races of one kind this election has; give each kind once")
    ap.add_argument("--reasons", help="also write the reasons here, one Markdown bullet each")
    ap.add_argument("--phase", action="store_true",
                    help="say where now falls for the shipped file's election, and what the "
                         "shipped file says of itself, and compare nothing")
    ap.add_argument("--tz", default="America/Chicago", help="the election's time zone")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not args.name:
        ap.error("--name is required")
    if args.phase:
        with open(os.path.join(REPO_ROOT, args.app_data, args.name + ".json"),
                  encoding="utf-8") as f:
            idx = json.load(f)
        m = re.search(r"/(\d+)/?$", str(idx.get("source") or ""))
        facts = {
            "phase": phase(idx["electionDate"],
                           datetime.datetime.now(datetime.timezone.utc), args.tz),
            "election_date": idx["electionDate"],
            "certified": "true" if idx.get("certified") else "false",
            # the publisher's page for this election, once a read has found it
            "results_id": m.group(1) if m else "",
            "counted": "true" if idx.get("contests") else "false",
        }
        for k, v in facts.items():
            print("%s=%s" % (k, v))
        out = os.environ.get("GITHUB_OUTPUT")
        if out:
            with open(out, "a", encoding="utf-8") as f:
                f.write("".join("%s=%s\n" % kv for kv in facts.items()))
        return
    expect = {}
    for e in args.expect:
        group, _, n = e.partition("=")
        if not group or not n.isdigit():
            ap.error("--expect %r is not GROUP=N" % e)
        expect[group] = int(n)
    new, new_parts = read_new(args.app_data, args.name)
    old, old_parts = read_old(args.app_data, args.name, args.base)
    verdict, reasons = judge(old, new, old_parts, new_parts, expect)
    for r in reasons:
        print("check-results-update: " + r)
    print("verdict: " + verdict)
    if args.reasons:
        with open(args.reasons, "w", encoding="utf-8") as f:
            f.write("".join("- %s\n" % r for r in reasons))
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write("verdict=%s\n" % verdict)


if __name__ == "__main__":
    main()
