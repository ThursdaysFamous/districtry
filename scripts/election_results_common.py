"""
The one writer for every app's election-results files, read by the engine's
election-results block (registerElectionResultsLayer). An app's builder reads
its own publisher, decides each contest's group, and hands the result here;
nothing in this module names a place or a publisher.

THE FILES. `<data/app>/election-results.json`, the index:

    election, electionDate, source, read, certified, certifiedDate, note,
    groups:    [{id, label, layer}]   race types in menu order, each tied to the
                                      map layer it is elected from, or null
    turnout:   {columns, total}       the area's registered voters and ballots
    precincts: [key, ...]             each precinct's key, exactly as the app's
                                      precinct layer writes the property the
                                      layer joins on (Chicago: ward_precinct)
    parts:     [part, ...]            aligned with precincts: which part file
                                      holds that precinct's own counts
    contests:  [{id, name, group, beyond, multiple, choices, total, leaders, margins}
                plus `from` where the strings are trimmed (below), and, only
                where an app's publisher gives them: outside, certified,
                certifiedDate, seats]

and one `<data/app>/election-results/<part>.json` per part, holding each of
its precincts' turnout [registered, ballots] and, per contest,
[contest id, votes in the contest, one count per choice in index order].

A contest's `leaders` holds one character per precinct, in `precincts` order:
the index (0-9 then a-z) of the choice with the most votes there, "=" for a
tie for the most, "?" where the publisher withholds a count (small-number
privacy filters; the withheld count is null in the part file), "." where the contest is on the ballot and no votes were
counted, and "-" where it is not on the ballot. The map colours a precinct
from this string alone, so it never downloads a part to draw.

THE STRINGS ARE TRIMMED: the run of "-" at either end of `leaders` is left out,
and `from` says which precinct the string starts at (absent when nothing is
trimmed at the start or end); a precinct outside the string is "-". Minnesota's
statewide file (5,177 contests over 4,105 precincts, most of them a city's,
town's or school district's) measured 43.7 MB untrimmed and 3.7 MB trimmed.

A contest's `margins` is aligned with `leaders`: how far the leader is ahead
of second place in that precinct, as a share of the votes counted there, in
five bands, "0" under 5 points, "1" 5 to 15, "2" 15 to 30, "3" 30 to 50 and
"4" 50 or more (MARGIN_BANDS), "0" for a tie and "-" where `leaders` names no
choice. The map draws a close race pale and a wide one strong (Adam,
2026-11-05, choosing the lead over second place over the leader's share,
which reads pale everywhere in a race with many candidates, and over the
votes cast, which shows turnout rather than how close it was).

`multiple` is true when some precinct counted more votes in the contest than
ballots were cast there, which happens only where a voter may choose more than
one candidate (Chicago's three six-year Water Reclamation seats), so the card
says its shares are of votes and not of voters.

THE OPTIONAL FIELDS are for publishers Chicago's Board is not, named so a
second app's builder passes them rather than reshaping the format:
  outside        [votes, one per choice] counted in no precinct shape (absentee,
                 early-voting and provisional units several states report on
                 their own); in `total`, never in a leader, and the card says
                 what share of the race the colours leave out
  certified,     one contest certified apart from the file (a locality
  certifiedDate  certifying its own offices before the state does)
  seats          how many the contest elects, where the publisher says; it
                 decides `multiple` whatever the counts show, which matters
                 where a publisher reports turnout apart from the counts
                 (Minnesota: 17 precincts showing a few more U.S. Senate votes
                 than voters on 5 November 2026); written to the index only
                 when more than one
What a builder resolves before it calls write_results, because only it knows
its publisher: one reporting unit covering several precinct shapes (give each
shape the unit's counts, or split them, and say which in the note), one
candidate on several ballot lines (sum the lines into one choice), and a
contest published in pieces per county (sum the pieces into one contest).

`beyond` is true when the contest's ground reaches past what the publisher
counts (a U.S. House district crossing the city line), so the card says its
totals are not the whole race.

WHY TWO KINDS OF FILE: measured on Chicago's 3 November 2026 general election
(219 contests, 1,291 precincts), the whole thing as one file was 2.6 MB, 851 KB
gzipped; the index is 22 KB gzipped and a ward's part 12 KB, so a click costs
about 34 KB rather than the whole city.
"""

import json
import os
import re

LEADER_CODES = "0123456789abcdefghijklmnopqrstuvwxyz"
INDEX_NAME = "election-results.json"
PART_DIR = "election-results"


MARGIN_BANDS = (5, 15, 30, 50)   # percentage points; a lead under the first is band 0


class ResultsError(Exception):
    pass


def leader_code(vals):
    """One character for one precinct of one contest; see the module's note."""
    if vals is None:
        return "-"
    counts = vals[1:]
    if any(n is None for n in counts):
        return "?"
    top = max(counts) if counts else 0
    if top == 0:
        return "."
    if counts.count(top) > 1:
        return "="
    return LEADER_CODES[counts.index(top)]


def margin_code(vals):
    """The band of the leader's lead over second place; see the module's note."""
    code = leader_code(vals)
    if code == "=":
        return "0"
    if code not in LEADER_CODES:
        return "-"
    counts = sorted(vals[1:], reverse=True)
    second = counts[1] if len(counts) > 1 else 0
    points = 100.0 * (counts[0] - second) / sum(counts)
    return str(sum(1 for edge in MARGIN_BANDS if points >= edge))


def write_results(app_data_dir, stamp, groups, turnout, contests, part_of, note):
    """Write the index and the part files.

    stamp:    {election, electionDate, source, read, certified, certifiedDate}
    groups:   [{id, label, layer}] in menu order; every contest's group must be one
    turnout:  {"total": [registered, ballots], "precincts": {key: [registered, ballots]}}
              naming every precinct the app draws, which fixes the key list
    contests: [{id, name, group, beyond, choices, total, precincts: {key: [votes, counts...]}}]
              in the order the menu lists them
    part_of:  key -> part id (a short string safe in a file name)
    Returns (number of contests, number of parts).
    """
    keys = sorted(turnout["precincts"])
    known = set(keys)
    group_ids = [g["id"] for g in groups]
    index = []
    parts = {}
    for c in contests:
        if c["group"] not in group_ids:
            raise ResultsError("%s: group %r is not in the groups list" % (c["name"], c["group"]))
        if not c["choices"]:
            raise ResultsError("%s names no choices" % c["name"])
        if len(c["choices"]) > len(LEADER_CODES):
            raise ResultsError("%s names %d choices; a leader string can name %d"
                               % (c["name"], len(c["choices"]), len(LEADER_CODES)))
        if not c["precincts"]:
            raise ResultsError("%s has no precincts" % c["name"])
        for k, vals in c["precincts"].items():
            if k not in known:
                raise ResultsError("%s: precinct %s is not one the app draws" % (c["name"], k))
            if len(vals) != len(c["choices"]) + 1:
                raise ResultsError("%s precinct %s: %d values for %d choices"
                                   % (c["name"], k, len(vals), len(c["choices"])))
            parts.setdefault(part_of(k), {}).setdefault(k, {"contests": []})["contests"].append(
                [c["id"]] + list(vals))
        cast = turnout["precincts"]
        entry = {
            "id": c["id"], "name": c["name"], "group": c["group"], "beyond": bool(c["beyond"]),
            "multiple": c["seats"] > 1 if c.get("seats") is not None else any(
                vals[0] is not None and cast[k][1] is not None and vals[0] > cast[k][1]
                for k, vals in c["precincts"].items() if k in cast),
            "choices": c["choices"], "total": c["total"],
        }
        leaders = "".join(leader_code(c["precincts"].get(k)) for k in keys)
        margins = "".join(margin_code(c["precincts"].get(k)) for k in keys)
        start = len(leaders) - len(leaders.lstrip("-"))
        end = len(leaders.rstrip("-"))
        if start or end < len(leaders):
            entry["from"] = start
        entry["leaders"] = leaders[start:end]
        entry["margins"] = margins[start:end]
        for opt in ("outside", "certified", "certifiedDate"):
            if c.get(opt) is not None:
                entry[opt] = c[opt]
        if (c.get("seats") or 1) > 1:
            entry["seats"] = c["seats"]
        if "outside" in entry and len(entry["outside"]) != len(c["choices"]) + 1:
            raise ResultsError("%s: outside has %d values for %d choices"
                               % (c["name"], len(entry["outside"]), len(c["choices"])))
        index.append(entry)
    for k, vals in turnout["precincts"].items():
        parts.setdefault(part_of(k), {}).setdefault(k, {"contests": []})["turnout"] = vals
    for p in parts:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", p):
            raise ResultsError("part id %r is not safe in a file name" % p)
    used = set(g for g in group_ids if any(c["group"] == g for c in contests))

    doc = dict(stamp)
    doc.update({
        "note": note,
        "groups": [g for g in groups if g["id"] in used],
        "turnout": {"columns": ["registered", "ballots"], "total": turnout["total"]},
        "precincts": keys,
        "parts": [part_of(k) for k in keys],
        "contests": index,
    })
    out_dir = os.path.join(app_data_dir, PART_DIR)
    if os.path.isdir(out_dir):
        for name in os.listdir(out_dir):
            if name.endswith(".json"):
                os.remove(os.path.join(out_dir, name))
    else:
        os.makedirs(out_dir)
    for p, precincts in sorted(parts.items()):
        pdoc = dict(stamp)
        pdoc.update({
            "part": p,
            "note": ("Each precinct's turnout [registered voters, ballots cast] and, per "
                     "contest, [contest id, votes in the contest, then one count per "
                     "choice in the order " + INDEX_NAME + " lists them]."),
            "precincts": dict(sorted(precincts.items())),
        })
        with open(os.path.join(out_dir, p + ".json"), "w") as fh:
            json.dump(pdoc, fh, separators=(",", ":"), ensure_ascii=False)
            fh.write("\n")
    with open(os.path.join(app_data_dir, INDEX_NAME), "w") as fh:
        json.dump(doc, fh, separators=(",", ":"), ensure_ascii=False)
        fh.write("\n")
    return len(index), len(parts)


def selftest():
    """Write a three-precinct fixture and read it back: one leader, a tie, a
    withheld count, a precinct with nothing counted, one off the ballot, a
    vote-for-two contest, and votes counted outside every precinct."""
    import tempfile
    stamp = {"election": "Test", "electionDate": "2026-11-03", "source": "https://example.invalid/",
             "read": "2026-11-05T00:00:00Z", "certified": False, "certifiedDate": None}
    groups = [{"id": "g", "label": "G", "layer": None}, {"id": "unused", "label": "U", "layer": None}]
    turnout = {"total": [300, 200], "precincts": {"01001": [100, 80], "01002": [100, 60], "02001": [100, 60]}}
    contests = [
        {"id": "1", "name": "One", "group": "g", "beyond": False, "choices": ["A", "B"],
         "total": [150, 70, 80], "outside": [20, 5, 15],
         "precincts": {"01001": [70, 50, 20], "01002": [40, 20, 20], "02001": [20, None, 20]}},
        {"id": "2", "name": "Two", "group": "g", "beyond": True, "choices": ["A", "B", "C"],
         "total": [0, 0, 0, 0], "precincts": {"01001": [100, 50, 40, 10], "01002": [0, 0, 0, 0]}},
        {"id": "3", "name": "Three", "group": "g", "beyond": False, "choices": ["A"], "seats": 1,
         "total": [70, 70], "precincts": {"02001": [70, 70]}},
    ]
    with tempfile.TemporaryDirectory() as d:
        n, parts = write_results(d, stamp, groups, turnout, contests, lambda k: "w" + k[:2], "note")
        idx = json.load(open(os.path.join(d, INDEX_NAME)))
        part = json.load(open(os.path.join(d, PART_DIR, "w01.json")))
    checks = [
        ((n, parts), (3, 2)),
        (idx["precincts"], ["01001", "01002", "02001"]),
        (idx["parts"], ["w01", "w01", "w02"]),
        ([g["id"] for g in idx["groups"]], ["g"]),
        (idx["contests"][0]["leaders"], "0=?"),
        (idx["contests"][0]["margins"], "30-"),   # 50 to 20 of 70 is 42.9 points; a tie; withheld
        (idx["contests"][1]["margins"], "1-"),    # 50 to 40 of 100 is 10 points; nothing counted; the off-ballot end trimmed
        (idx["contests"][1]["leaders"], "0."),
        (idx["contests"][1].get("from"), 0),
        ("from" in idx["contests"][0], False),
        (idx["contests"][2]["leaders"], "0"), (idx["contests"][2]["from"], 2),
        (idx["contests"][2]["multiple"], False),  # 70 votes against 60 ballots, but one seat
        ("seats" in idx["contests"][2], False),
        (margin_code([10, 10, 0]), "4"), (margin_code([100, 52, 47, 1]), "1"),
        (margin_code([100, 51, 49]), "0"),
        (idx["contests"][0]["outside"], [20, 5, 15]),
        (idx["contests"][0]["multiple"], False),
        (idx["contests"][1]["multiple"], True),   # 100 votes against 80 ballots in 01001
        ("outside" in idx["contests"][1], False),
        (part["precincts"]["01001"]["turnout"], [100, 80]),
        (part["precincts"]["01001"]["contests"], [["1", 70, 50, 20], ["2", 100, 50, 40, 10]]),
    ]
    bad = [(got, want) for got, want in checks if got != want]
    for got, want in bad:
        print("election-results-common selftest: got %r, want %r" % (got, want))
    for broken, why in (
        (dict(contests[0], group="nope"), "unknown group"),
        (dict(contests[0], precincts={"99999": [1, 1, 0]}), "unknown precinct"),
        (dict(contests[0], outside=[1, 1]), "short outside"),
    ):
        try:
            with tempfile.TemporaryDirectory() as d:
                write_results(d, stamp, groups, turnout, [broken], lambda k: "w" + k[:2], "note")
            bad.append((why, "accepted"))
            print("election-results-common selftest: %s was accepted" % why)
        except ResultsError:
            pass
    if bad:
        raise SystemExit(1)
    print("election-results-common selftest: OK — %d checks and 3 refusals" % len(checks))


if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["--selftest"]:
        selftest()
    else:
        raise SystemExit("usage: election_results_common.py --selftest")
