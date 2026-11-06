#!/usr/bin/env python3
"""
Build va/data/app/election-results.json and its locality files from the raw
read made by va_election_results_scraper.py: every contest the Virginia
Department of Elections reports by precinct for one election, each precinct's
votes for each choice, grouped by the map layer the contest is elected from, so
the Election Results card can offer the races on the clicked precinct's ballot
by layer and the map can fill each precinct by the choice with the most votes
there.

THE PRECINCT KEY is the Voting Precinct layer's own `key`
(data/app/va-precincts.json, the Department's precinct shapes): "51", the
three-digit locality code, a hyphen, and the precinct id padded to six digits
(Accomack's 0101 is 51001-000101). Measured on the 3 November 2026 file: 2,529
precincts, every one of them a key the layer draws; the layer's other two
(Fairfax County's 700 and Richmond County's 502) report no votes and are left
uncoloured. More than MAX_UNREPORTED drawn precincts missing from the file, or
any precinct in the file the layer does not draw, fails the build, since that
means the layer and the Department's precincts have parted. The names the two
print sometimes differ (the layer's "Venable" is the file's "202 -
TRAILBLAZER"), and the key is the number, not the name.

EVERY VOTE IS IN A PRECINCT: the Department assigns early, mailed and
provisional ballots to their voter's precinct (see the scraper), so no contest
has `outside` counts.

WHAT A CONTEST IS: one OfficeId and DistrictId. The file's DistrictType places
it: state (the U.S. Senate, and the constitutional amendments), congressional,
state-house (a special election for one House of Delegates seat), county and
city (a whole county's or independent city's offices and questions), town (a
whole town's), and other (a district of a county or city, or a ward of a town).
GROUP_RULES turns those into the race menu's groups and the layer each is drawn
on; a contest no rule places fails the build, so a new kind is placed by a
person rather than dropped.

NAMES. The file's office title, with the locality added where the title does
not already say where ("Member School Board (District 1)" becomes "Member
School Board (District 1), Isle of Wight County"), because a precinct's menu
can hold district seats from more than one body.

CHOICES. The order the file lists a contest's choices in is not shown to be
the ballot's, so the choices are ordered by a rule that cannot lean: Yes, then
No, for a question; otherwise by surname, with the write-ins last. A contest's
write-in lines are summed into one Write-in choice. A choice's colour is that
position, never its party.

SEATS come from the file's own NumberOfSeats column.

TURNOUT. The Department's turnout report leaves ballots cast blank for about
half the precincts, so each precinct's turnout is [null, null] and the card says
nothing about turnout.

UNOFFICIAL UNTIL CERTIFIED. The file carries `certified: false` and the time it
was read. When the State Board of Elections certifies the results, run the build
with `--certified <date>`.

Usage:
    python3 va/scripts/build_va_election_results.py /tmp/va_results_raw.json \
        --election-date 2026-11-03 [--certified YYYY-MM-DD]
"""

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
FLEET_SCRIPTS = os.path.join(os.path.dirname(INSTANCE), "scripts")
sys.path.insert(0, FLEET_SCRIPTS)

from election_results_common import ResultsError, write_results  # noqa: E402
from scraper_common import make_fail  # noqa: E402

fail = make_fail("build-va-election-results")

APP_DATA = os.path.join(INSTANCE, "data", "app")
PRECINCTS = os.path.join(APP_DATA, "va-precincts.json")
MIN_CONTESTS = 300
PART_SIZE = 60
MAX_UNREPORTED = 5
EXPECTED_LOCALITIES = 133
WRITE_IN = "Write-in"

# (group id, label shown in the race menu, the map layer it is elected from or
# None, the district types it takes, a pattern the office title matches or
# None for any, whether it takes only questions (True), only offices (False)
# or both (None)). First match wins.
GROUP_RULES = [
    ("statewide", "U.S. Senate", None, ("state",), r"United States Senate", False),
    ("questions", "Constitutional amendments", None, ("state",), None, True),
    ("us-house", "U.S. House", "us-house", ("congressional",), r"House of Representatives", False),
    ("va-house", "House of Delegates", "va-house", ("state-house",), r"House of Delegates", False),
    ("locality", "County and city offices", "county", ("county", "city"), None, False),
    ("locality-questions", "County and city questions", "county", ("county", "city"), None, True),
    ("supervisor-district", "Supervisors and council by district", "supervisor-district",
     ("other",), r"Board of Supervisors|City Council|County Board", False),
    ("school-board-district", "School board by district", "school-board-district",
     ("other",), r"School Board", False),
    ("shared", "Offices shared by a county and a city", "county", ("other",),
     r"^(Sheriff|Clerk|Commonwealth's Attorney|Treasurer|Commissioner of the Revenue)\b", False),
    ("town", "Town offices and questions", "municipality", ("town",), None, None),
    ("town-ward", "Town council by ward", None, ("other",), r"Town Council", False),
]
GROUP_ORDER = [g[0] for g in GROUP_RULES]
SUFFIXES = {"JR", "JR.", "SR", "SR.", "II", "III", "IV"}
FIRST = {"YES": 0, "FOR": 0, "NO": 1, "AGAINST": 1}
SMALL = {"of", "and", "the"}


def is_write_in(candidate_id, choice):
    return candidate_id.startswith("wi-") or re.fullmatch(r"(?i)write[ -]?in( votes)?", choice) is not None


def group_of(dtype, office, question):
    for gid, _label, _layer, types, pattern, only in GROUP_RULES:
        if dtype not in types:
            continue
        if pattern and not re.search(pattern, office):
            continue
        if only is not None and only != question:
            continue
        return gid
    fail("no group places %s contest %r%s; add a rule to GROUP_RULES"
         % (dtype, office, " (a question)" if question else ""))


def title_case(name):
    words = name.lower().split()
    return " ".join(w if (i and w in SMALL) else w[:1].upper() + w[1:] for i, w in enumerate(words))


def contest_name(office, dtype, locality):
    name = re.sub(r"\s+", " ", office).strip()
    if dtype in ("state", "congressional", "state-house", "town"):
        return name
    place = title_case(locality)
    stem = re.sub(r" (County|City)$", "", place)
    if stem.lower() in name.lower():
        return name
    return "%s, %s" % (name, place)


def natural(s):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]


def choice_order(choice):
    """Questions Yes then No; people by surname; the write-ins last."""
    up = choice.upper()
    if up in FIRST:
        return (0, FIRST[up], "")
    if choice == WRITE_IN:
        return (2, 0, up)
    words = [w for w in re.sub(r"\([^)]*\)", " ", up).replace(",", " ").split() if w not in SUFFIXES]
    return (1, 0, (words[-1] if words else up) + " " + up)


def layer_keys():
    doc = json.load(open(PRECINCTS))
    keys = {}
    for f in doc["features"]:
        p = f["properties"]
        keys[str(p["key"])] = p
    localities = {k[:5] for k in keys}
    if len(localities) != EXPECTED_LOCALITIES:
        fail("the precinct layer names %d localities, expected %d"
             % (len(localities), EXPECTED_LOCALITIES))
    return keys


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("raw")
    ap.add_argument("--election-date", required=True)
    ap.add_argument("--certified", help="the date the State Board of Elections certified the results")
    ap.add_argument("--app-data", default=APP_DATA, help="the app's data/app directory (default: va/data/app)")
    args = ap.parse_args()

    raw = json.load(open(args.raw))
    cols = raw["columns"]
    allowed = layer_keys()

    contests = {}
    seen = set()
    undrawn = set()
    for row in raw["rows"]:
        r = dict(zip(cols, row))
        key = "51%s-%s" % (r["localityCode"], r["precinctId"].zfill(6))
        if key not in allowed:
            undrawn.add("%s (%s, %s)" % (key, r["precinct"], r["locality"]))
            continue
        seen.add(key)
        ident = (r["officeId"], r["districtId"])
        choice = WRITE_IN if is_write_in(r["candidateId"], r["choice"]) else re.sub(r"\s+", " ", r["choice"])
        c = contests.get(ident)
        if c is None:
            c = contests[ident] = {"ident": ident, "office": r["office"], "dtype": r["districtType"],
                                   "locality": r["locality"], "seats": r["seats"],
                                   "choices": {}, "precincts": {}}
        if (c["office"], c["dtype"]) != (r["office"], r["districtType"]):
            fail("contest %s/%s is both %r (%s) and %r (%s)" % (ident + (c["office"], c["dtype"],
                 r["office"], r["districtType"])))
        if c["seats"] != r["seats"]:
            fail("%s: NumberOfSeats is both %d and %d" % (c["office"], c["seats"], r["seats"]))
        c["choices"][choice] = True
        counts = c["precincts"].setdefault(key, {})
        if choice in counts and choice != WRITE_IN:
            fail("%s: precinct %s lists %r twice" % (c["office"], key, choice))
        counts[choice] = counts.get(choice, 0) + r["votes"]

    if undrawn:
        fail("%d precincts in the file are not on the layer: %s"
             % (len(undrawn), "; ".join(sorted(undrawn)[:20])))
    unreported = sorted(set(allowed) - seen)
    if len(unreported) > MAX_UNREPORTED:
        fail("%d precincts the layer draws are not in the file (at most %d allowed): %s"
             % (len(unreported), MAX_UNREPORTED, ", ".join(unreported[:20])))

    out = []
    used = set()
    for c in contests.values():
        choices = sorted(c["choices"], key=choice_order)
        question = set(ch.upper() for ch in choices) <= {"YES", "NO"}
        group = group_of(c["dtype"], c["office"], question)
        name = contest_name(c["office"], c["dtype"], c["locality"])
        precincts = {}
        for k, counts in c["precincts"].items():
            vals = [counts.get(ch, 0) for ch in choices]
            missing = [ch for ch in choices if ch not in counts and ch != WRITE_IN]
            if missing:
                fail("%s: precinct %s does not list %s" % (name, k, ", ".join(missing)))
            precincts[k] = [sum(vals)] + vals
        total = [0] * (len(choices) + 1)
        for vals in precincts.values():
            total = [a + b for a, b in zip(total, vals)]
        base = "c" + re.sub(r"[^a-z0-9]+", "-", ("%s-%s" % c["ident"]).lower()).strip("-")[:48]
        cid, n = base, 1
        while cid in used:
            n += 1
            cid = "%s-%d" % (base, n)
        used.add(cid)
        out.append({
            "id": cid, "name": name, "group": group, "beyond": False,
            "choices": choices, "total": total, "precincts": precincts, "seats": c["seats"],
            "_sort": (GROUP_ORDER.index(group), natural(name)),
        })
    if len(out) < MIN_CONTESTS:
        fail("only %d contests; expected at least %d" % (len(out), MIN_CONTESTS))
    out.sort(key=lambda c: c.pop("_sort"))

    turnout = {"total": [None, None], "precincts": dict((k, [None, None]) for k in allowed)}
    groups = [{"id": g[0], "label": g[1], "layer": g[2]} for g in GROUP_RULES]
    stamp = {
        "election": "General Election",
        "electionDate": args.election_date,
        "source": raw["page"],
        "read": raw["read"],
        "certified": bool(args.certified),
        "certifiedDate": args.certified or None,
    }
    note = ("Unofficial results as the Virginia Department of Elections publishes them by "
            "precinct (its Election Results report), until the State Board of Elections "
            "certifies them (certified then reads true). Precinct keys are the Voting Precinct "
            "layer's key: 51, the locality code, a hyphen and the Department's precinct id "
            "padded to six digits. The Department assigns early, mailed and provisional ballots "
            "to their precinct, so no contest has outside counts. The file reports no complete "
            "turnout. Each precinct's counts are in a part file named for its locality (c + the "
            "locality's FIPS code) and a run of up to 60 of that locality's precincts in key "
            "order. The layout is scripts/election_results_common.py's.")
    part = {}
    by_locality = {}
    for k in sorted(allowed):
        by_locality.setdefault(k[2:5], []).append(k)
    for lf, keys in by_locality.items():
        for i, k in enumerate(keys):
            part[k] = "c%s-%d" % (lf, i // PART_SIZE + 1)
    try:
        n, nparts = write_results(args.app_data, stamp, groups, turnout, out, part.get, note)
    except ResultsError as e:
        fail(str(e))
    by = {}
    for c in out:
        by[c["group"]] = by.get(c["group"], 0) + 1
    print("wrote %d contests (%s), %d part files under %s; drawn precincts with no votes: %s"
          % (n, ", ".join("%s %d" % (g, by[g]) for g in GROUP_ORDER if g in by), nparts,
             os.path.relpath(args.app_data), ", ".join(unreported) or "none"), file=sys.stderr)


if __name__ == "__main__":
    main()
